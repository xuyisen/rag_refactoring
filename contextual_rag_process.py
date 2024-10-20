import json
import os

from langchain_core.messages import HumanMessage
from langchain_core.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

# OpenAI API key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# 创建一个LangChain模型
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=OPENAI_API_KEY)

# Load JSON data from the specified file path
def load_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

# Save updated JSON data to a new file
def save_json(output_file_path, data):
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# Load the prompt text from the specified file path
def load_prompt_template(prompt_path):
    with open(prompt_path, 'r', encoding='utf-8') as f:
        return f.read().strip()

# Generate a context description using the required fields
def generate_context_description(refactoring):
    context_description = (
        f"PackageName: {refactoring.get('packageNameBefore', '')}\n"
        f"ClassName: {refactoring.get('classNameBefore', '')}\n"
        f"MethodName: {refactoring.get('methodNameBefore', '')}\n"
        f"ClassSignature: {refactoring.get('classSignatureBefore', '')}\n"
    )

    # Include invokedMethod if available
    invoked_method = refactoring.get('invokedMethod', '')
    if invoked_method:
        context_description += f"InvokedMethod:\n{invoked_method}\n"

    # Include the chunk (code before refactoring)
    chunk = refactoring.get('sourceCodeBeforeRefactoring', '')
    if chunk:
        context_description += f"\nCode:\n{chunk}\n"

    return context_description

# Process commits with filtering and limit on the number of refactorings
def process_commits(file_path, prompt_file_path, output_file_path, limit=None):
    data = load_json(file_path)
    commits = data.get("commits", [])
    count = 0  # Track the number of processed refactorings
    prompt_template = load_prompt_template(prompt_file_path)

    for commit in commits:
        for refactoring in commit.get('refactorings', []):
            # Filter only pure refactorings
            if not refactoring.get('isPureRefactoring', False):
                continue

            # Generate and print the context description
            context_description = generate_context_description(refactoring)
            source_code_content = refactoring.get('sourceCodeBeforeRefactoring', '')
            prompt = PromptTemplate(
                input_variables=["WHOLE_CONTEXT", "SOURCE_CODE"],
                template=prompt_template,
            )
            print(f"Context Description:\n{context_description}\n")

            # Generate the final prompt
            final_prompt = prompt.format(
                WHOLE_CONTEXT=context_description.strip(),
                SOURCE_CODE=source_code_content.strip(),
            )

            print(final_prompt)
            # Call the LLM to generate the refactored code
            messages = [HumanMessage(content=final_prompt)]
            result = llm.invoke(messages).content
            print(result)
            refactoring['contextDescription'] = result

            # Increment the counter and stop if the limit is reached
            count += 1
            # if limit and count >= limit:
            #     print(f"Processed {count} refactorings (limit reached).")
            #     save_json(output_file_path, data)  # Save the updated data to the new file
            #     return
    save_json(output_file_path, data)
    print(f"Processed {count} refactorings.")

if __name__ == "__main__":
    input_json_path = 'data/refactoring_info/refactoring_miner_em_refactoring_w_sc_v2.json'  # Path to the input JSON file
    output_json_path = 'data/output/refactoring_miner_em_refactoring_context_w_sc_v2.json'  # Path for the output JSON file
    prompt_file_path = 'data/prompts/context_refactoring_prompt.txt'  # Path to the prompt file

    process_commits(input_json_path, prompt_file_path, output_json_path, limit=600)  # Process up to 5 refactorings