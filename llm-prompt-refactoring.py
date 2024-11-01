import json
import os
from langchain.prompts import PromptTemplate
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from openai import OpenAI

from bm25 import BM25
from rag_embedding import search_chroma, remove_java_comments
from reciprocal_rank_fusion import ReciprocalRankFusion
from refactoring_entity import RefactoringRepository
from reranking import Reranking
from util import project_name

# OpenAI API key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# 创建一个LangChain模型
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=OPENAI_API_KEY)

client = OpenAI()

# 调用 search_chroma 获取历史重构例子
def get_historical_refactorings(search_text, refactoring_map, bm25_model):
    # get embedding search result
    embedding_result = search_chroma(search_text, n_results=10, collection_name='refactoring_miner_em_wc_context_collection')
    embedding_document = embedding_result['documents'][0]
    # get BM25 search result
    bm25_document = bm25_model.search(search_text, top_n=10)
    # reciprocal rank fusion
    ranked_lists = [embedding_document, bm25_document]
    rrf = ReciprocalRankFusion(k=60)

    scores = rrf.fuse(ranked_lists)
    print("RRF Scores:", scores)

    # Get the top 10 documents
    top_docs = rrf.get_top_n(scores, n=10)
    print("Top 10 Documents:", top_docs)

    top_docs_text = [doc[0] for doc in top_docs]
    # Reranking the top 10 documents
    reranker = Reranking("colbert")
    query = search_text
    ranked_results = reranker.rerank(query, top_docs_text)
    top_ranked_result = ranked_results.top_k(3)
    metadata_refactoring = []
    for result in top_ranked_result:
        print(f"Rank: {result.rank}, Score: {result.score}, Document: {result.document.text}")
        metadata_refactoring.append(refactoring_map[result.document.text])
    search_result = "\n".join([
        f"Example {i + 1}:\n SourceCodeBeforeRefactoring:\n {example['sourceCodeBeforeRefactoring']}\n SourceCodeAfterRefactoring:\n{example['sourceCodeAfterRefactoring']}\n DiffSourceCode:\n{example['diffSourceCode']}\n"
        for i, example in enumerate(metadata_refactoring)
    ])
    return search_result


# 从文件中读取 prompt 模板
def load_prompt_template(prompt_file_path):
    with open(prompt_file_path, 'r') as prompt_file:
        return prompt_file.read()

# Function to save refactoring results to a file
def save_refactoring_results(output_file_path, results):
    with open(output_file_path, 'w') as output_file:
        json.dump(results, output_file, indent=4)

# def refactor_code(to_be_refactored_code):
#     # 1. 任务介绍
#     task_description = """
#            You are an expert software engineer. Your task is to refactor the following code to improve its readability and efficiency without changing its functionality.
#            """
#
#     # 2. 读取文件路径中的prompt模板
#     prompt_file_path = 'data/prompts/refactoring_prompt_v1.txt'
#     prompt_template = load_prompt_template(prompt_file_path)
#     historical_refactorings = "get_historical_refactorings(to_be_refactored_code)"
#     print(historical_refactorings)
#     # Create a PromptTemplate instance
#     prompt = PromptTemplate(
#         input_variables=["task_description", "historical_refactorings", "code_to_refactor"],
#         template=prompt_template,
#     )
#     # Create a PromptTemplate instance
#     prompt = PromptTemplate(
#         input_variables=["task_description", "historical_refactorings", "code_to_refactor"],
#         template=prompt_template,
#     )
#
#     # Generate the final prompt
#     final_prompt = prompt.format(
#         task_description=task_description.strip(),
#         historical_refactorings=historical_refactorings.strip(),
#         code_to_refactor=to_be_refactored_code
#     )
#
#     # Call the LLM to generate the refactored code
#     messages = [HumanMessage(content=final_prompt)]
#     refactored_code = llm.invoke(messages).content
#     print(refactored_code)

# Function to process each commit and refactor the code
def process_commits(commits, output_file_path, num_count):

    # 1. 任务介绍
    task_description = """
       You are an expert software engineer. You are given a large or complex method that contains multiple responsibilities. The objective is to refactor this method by extracting smaller, cohesive methods that represent distinct tasks. This refactoring will improve code readability, maintainability, and modularity.
       """

    # 2. 读取文件路径中的prompt模板
    prompt_file_path = 'data/prompts/refactoring_prompt_v2.txt'
    prompt_template = load_prompt_template(prompt_file_path)
    refactoring_results = []

    refactoring_map = RefactoringRepository.load_from_file("data/refactoring_info/refactoring_map_em_wc_v2.json",
                                                           format="json")

    bm25_model = BM25.load_model('data/model/refactoring_miner_em_wc_context_collection_bm25result.pkl')

    count = 0
    commits.reverse()
    for commit in commits:
        commitId = commit['commitId']
        branch = commit['branch']
        url = commit['url']
        if "refactorings" not in commit:
            continue
        for refactoring in commit['refactorings']:
            if count >= num_count:
                break
            # Get the source code before refactoring
            source_code_before_refactoring = refactoring['sourceCodeBeforeRefactoring']
            source_code_after_refactoring = refactoring['sourceCodeAfterRefactoring']
            diff_source_code = refactoring['diffSourceCode']
            if not refactoring['isPureRefactoring']:
                continue
            # Get historical refactoring examples
            historical_refactorings = get_historical_refactorings(source_code_before_refactoring, refactoring_map, bm25_model)
            print(historical_refactorings)

            context_description = f"PackageName: {refactoring['packageNameBefore']}\nClassName: {refactoring['classNameBefore']}\nMethodName: {refactoring['methodNameBefore']}\n ClassSignature: {refactoring['classSignatureBefore']}\n"
            if "invokedMethod" in refactoring:
                context_description += f"InvokedMethod: {refactoring['invokedMethod']}"
            # Create a PromptTemplate instance
            prompt = PromptTemplate(
                input_variables=["task_description", "historical_refactorings", "code_to_refactor", "context_description"],
                template=prompt_template,
            )

            # Generate the final prompt
            final_prompt = prompt.format(
                task_description=task_description.strip(),
                historical_refactorings=historical_refactorings.strip(),
                code_to_refactor=source_code_before_refactoring.strip(),
                context_description=context_description.strip()
            )
            print(final_prompt)
            META_PROMPT = load_prompt_template('data/prompts/meta_prompt.txt')
            updated_prompt = generate_prompt(final_prompt, META_PROMPT)
            # Call the LLM to generate the refactored code
            messages = [HumanMessage(content=updated_prompt)]
            refactored_code = llm.invoke(messages).content
            print(refactored_code)
            # Collect the result for this commit
            refactoring_results.append({
                "url": url,
                "branch": branch,
                "commitId": commitId,
                "sourceCodeBeforeRefactoring": source_code_before_refactoring,
                "refactoredCode": refactored_code,
                "sourceCodeAfterRefactoring": source_code_after_refactoring,
                "diffSourceCode": diff_source_code,
                "uniqueId": refactoring['uniqueId'],
                "historicalRefactorings": historical_refactorings,
                "contextDescription": context_description,
                "prompt": final_prompt,
                "updatedPrompt": updated_prompt
            })
            count += 1

    # Save all results to a file
    save_refactoring_results(output_file_path, refactoring_results)






def generate_prompt(task_or_prompt: str, META_PROMPT: str):
    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": META_PROMPT,
            },
            {
                "role": "user",
                "content": "Task, Goal, or Current Prompt:\n" + task_or_prompt,
            },
        ],
    )

    return completion.choices[0].message.content

    return json.loads(completion.choices[0].message.content)
if __name__ == "__main__":
    # project_name = 'gson'
    # Load the JSON data with commits and refactorings
    file_path = 'data/refactoring_info/refactoring_miner_em_refactoring_context_w_sc_v2.json'
    with open(file_path, 'r') as file:
        data = json.load(file)

    # Process all commits and save results
    output_file_path = 'data/output/refactoring_miner_em_refactoring_context_result_meta_prompt_w_sc_v2.json'
    process_commits(data['commits'], output_file_path, 10)

    # Print confirmation
    print(f"Refactored code for all commits saved to {output_file_path}")

#     code_to_refactor = """
#     public WndEnergizeItem(Item item, WndBag owner) {
# 		super(item);
#
# 		this.owner = owner;
#
# 		float pos = height;
#
# 		if (item.quantity() == 1) {
#
# 			RedButton btnEnergize = new RedButton( Messages.get(this, "energize", item.energyVal()) ) {
# 				@Override
# 				protected void onClick() {
# 					energize( item );
# 					hide();
# 				}
# 			};
# 			btnEnergize.setRect( 0, pos + GAP, width, BTN_HEIGHT );
# 			btnEnergize.icon(new ItemSprite(ItemSpriteSheet.ENERGY));
# 			add( btnEnergize );
#
# 			pos = btnEnergize.bottom();
#
# 		} else {
#
# 			int energyAll = item.energyVal();
# 			RedButton btnEnergize1 = new RedButton( Messages.get(this, "energize_1", energyAll / item.quantity()) ) {
# 				@Override
# 				protected void onClick() {
# 					energizeOne( item );
# 					hide();
# 				}
# 			};
# 			btnEnergize1.setRect( 0, pos + GAP, width, BTN_HEIGHT );
# 			btnEnergize1.icon(new ItemSprite(ItemSpriteSheet.ENERGY));
# 			add( btnEnergize1 );
# 			RedButton btnEnergizeAll = new RedButton( Messages.get(this, "energize_all", energyAll ) ) {
# 				@Override
# 				protected void onClick() {
# 					energize( item );
# 					hide();
# 				}
# 			};
# 			btnEnergizeAll.setRect( 0, btnEnergize1.bottom() + 1, width, BTN_HEIGHT );
# 			btnEnergizeAll.icon(new ItemSprite(ItemSpriteSheet.ENERGY));
# 			add( btnEnergizeAll );
#
# 			pos = btnEnergizeAll.bottom();
#
# 		}
#
# 		resize( width, (int)pos );
#
# 	}
#
# 	public static void energizeOne( Item item ) {
#
# 		if (item.quantity() <= 1) {
# 			energize( item );
# 		} else {
#
# 			Hero hero = Dungeon.hero;
#
# 			item = item.detach( hero.belongings.backpack );
#
# 			if (ShatteredPixelDungeon.scene() instanceof AlchemyScene){
#
# 				Dungeon.energy += item.energyVal();
# 				((AlchemyScene) ShatteredPixelDungeon.scene()).createEnergy();
#
# 			} else {
#
# 				//selling items in the sell interface doesn't spend time
# 				hero.spend(-hero.cooldown());
#
# 				new EnergyCrystal(item.energyVal()).doPickUp(hero);
# 			}
# 		}
# 	}
#
# public static void energize( Item item ) {
#
# 		Hero hero = Dungeon.hero;
#
# 		if (item.isEquipped( hero ) && !((EquipableItem)item).doUnequip( hero, false )) {
# 			return;
# 		}
# 		item.detachAll( hero.belongings.backpack );
#
# 		if (ShatteredPixelDungeon.scene() instanceof AlchemyScene){
#
# 			Dungeon.energy += item.energyVal();
# 			((AlchemyScene) ShatteredPixelDungeon.scene()).createEnergy();
#
# 		} else {
#
# 			//selling items in the sell interface doesn't spend time
# 			hero.spend(-hero.cooldown());
#
# 			new EnergyCrystal(item.energyVal()).doPickUp(hero);
#
# 		}
# 	}
# 	"""
#
#     refactor_code(code_to_refactor)

