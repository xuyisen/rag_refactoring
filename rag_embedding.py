import json
import re

import chromadb

from bm25 import BM25

chroma_client = chromadb.HttpClient(host='localhost', port=8000)
from chromadb.utils import embedding_functions

# refactoring_em_wc_collection 有注释的数据库
# refactoring_em_woc_collection 无注释的数据库
def remove_java_comments(java_code):
    # 匹配单行注释 //... 和 多行注释 /*...*/、/**...*/
    pattern = r"(//.*?$|/\*.*?\*/|/\*\*.*?\*/)"
    # 使用 re.sub 移除匹配的注释
    cleaned_code = re.sub(pattern, "", java_code, flags=re.DOTALL | re.MULTILINE)
    return cleaned_code


# Create a new collection
default_ef = embedding_functions.DefaultEmbeddingFunction();
# chroma_client.delete_collection(name="refactoring_collection")


#读取 JSON 文件
# with open('data/junit4_em_refactoring_w_sc_result.json', 'r') as file:
#     data = json.load(file)

def add_documents_to_chroma(collection_name, file_path, num_count):
    collection = chroma_client.get_or_create_collection(name=collection_name)
    # 创建要写入 Chroma 的 documents 和 ids
    with open(file_path, 'r') as file:
        data = json.load(file)
    documents = []
    metadata_refactoring = []
    ids = []
    unique_ids_set = set()  # 用于存储已经添加的 uniqueId
    count = 0
    # 遍历 JSON 中的 commits
    for commit in data['commits']:
        if "refactorings" not in commit:
            continue
        if count >= num_count:
            break
        for refactoring in commit['refactorings']:
            unique_id = refactoring['uniqueId']

            # 检查是否已经存在该 uniqueId
            if unique_id not in unique_ids_set and refactoring['isPureRefactoring']:
                # 获取所需字段
                source_before = remove_java_comments(refactoring['sourceCodeBeforeRefactoring'])
                context_description = refactoring['contextDescription']
                refactoring_data_to_store = {
                    "type": "Extract Method",
                    "sourceCodeBeforeRefactoring": refactoring['sourceCodeBeforeRefactoring'],
                    "filePathBefore": refactoring['filePathBefore'],
                    "isPureRefactoring": refactoring['isPureRefactoring'],
                    "commitId": refactoring['commitId'],
                    "packageNameBefore": refactoring['packageNameBefore'],
                    "classNameBefore": refactoring['classNameBefore'],
                    "methodNameBefore": refactoring['methodNameBefore'],
                    "invokedMethod": "invokedMethod" in refactoring and refactoring['invokedMethod'] or "",
                    "classSignatureBefore": refactoring['classSignatureBefore'],
                    "sourceCodeAfterRefactoring": refactoring['sourceCodeAfterRefactoring'],
                    "diffSourceCode": refactoring['diffSourceCode'],
                    "uniqueId": refactoring['uniqueId'],
                    "contextDescription": refactoring['contextDescription'],
            }

                # 添加到 documents 和 ids
                documents.append(context_description + '\n' + source_before)
                metadata_refactoring.append(refactoring_data_to_store)
                ids.append(unique_id)
                count += 1

                # 将 uniqueId 加入 set，避免重复添加
                unique_ids_set.add(unique_id)
            else:
                if unique_id in unique_ids_set:
                    print(f"Skipping duplicate uniqueId: {unique_id}")


    # 将去重后的数据写入 Chroma
    if documents:
        collection.add(
            documents=documents,
            metadatas=metadata_refactoring,
            ids=ids,
        )
        # add document to bm25
        bm25_model = BM25(documents)
        bm25_model.save_model(f'data/model/{collection_name}_bm25result.pkl')
    else:
        print("No new unique IDs to add.")

def search_chroma(text,n_results,collection_name):

    collection = chroma_client.get_or_create_collection(name=collection_name)
    # 测试查询功能
    results = collection.query(
        query_texts=[text],  # 这是你要查询的文本
        n_results=n_results  # 返回的结果数
    )
    return results

if __name__ == "__main__":
    connection = chroma_client.get_or_create_collection(name='refactoring_miner_em_wc_context_collection')
    print(connection.count())
    # chroma_client.delete_collection(name='refactoring_miner_em_wc_collection')
    add_documents_to_chroma('refactoring_miner_em_wc_context_collection', 'data/refactoring_info/refactoring_miner_em_refactoring_context_w_sc_v2.json', 200)
    # result = search_chroma("@Override\n    public void start() {\n        mStorageManager = (StorageManager) mContext.getSystemService(Context.STORAGE_SERVICE);\n        final boolean connected = mStorageManager.isUsbMassStorageConnected();\n        if (DEBUG) Log.d(TAG, String.format( \"Startup with UMS connection %s (media state %s)\",\n                mUmsAvailable, Environment.getExternalStorageState()));\n\n        HandlerThread thr = new HandlerThread(\"SystemUI StorageNotification\");\n        thr.start();\n        mAsyncEventHandler = new Handler(thr.getLooper());\n\n        StorageNotificationEventListener listener = new StorageNotificationEventListener();\n        listener.onUsbMassStorageConnectionChanged(connected);\n        mStorageManager.registerListener(listener);\n    }", 3, 'refactoring_miner_em_wc_collection')
    # print(result)