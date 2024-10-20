import json
import pickle

from rag_embedding import remove_java_comments


class Refactoring:
    def __init__(self, refactoring_data):
        """初始化 Refactoring 对象。"""
        self.type = refactoring_data.get("type")
        self.source_code_before = refactoring_data.get("sourceCodeBeforeRefactoring")
        self.file_path_before = refactoring_data.get("filePathBefore")
        self.is_pure_refactoring = refactoring_data.get("isPureRefactoring", False)
        self.commit_id = refactoring_data.get("commitId")
        self.package_name_before = refactoring_data.get("packageNameBefore")
        self.class_name_before = refactoring_data.get("classNameBefore")
        self.method_name_before = refactoring_data.get("methodNameBefore")
        self.invoked_method = refactoring_data.get("invokedMethod", "")
        self.class_signature_before = refactoring_data.get("classSignatureBefore")
        self.source_code_after = refactoring_data.get("sourceCodeAfterRefactoring")
        self.diff_source_code = refactoring_data.get("diffSourceCode")
        self.unique_id = refactoring_data.get("uniqueId")
        self.context_description = refactoring_data.get("contextDescription")

    def to_dict(self):
        """将 Refactoring 对象转换为字典，便于序列化存储。"""
        return {
            "type": self.type,
            "sourceCodeBeforeRefactoring": self.source_code_before,
            "filePathBefore": self.file_path_before,
            "isPureRefactoring": self.is_pure_refactoring,
            "commitId": self.commit_id,
            "packageNameBefore": self.package_name_before,
            "classNameBefore": self.class_name_before,
            "methodNameBefore": self.method_name_before,
            "invokedMethod": self.invoked_method,
            "classSignatureBefore": self.class_signature_before,
            "sourceCodeAfterRefactoring": self.source_code_after,
            "diffSourceCode": self.diff_source_code,
            "uniqueId": self.unique_id,
            "contextDescription": self.context_description,
        }


class RefactoringRepository:
    def __init__(self, data):
        self.refactoring_map = self._build_map(data)

    def _build_map(self, data):
        """构建以 contextDescription 为键的字典。"""
        refactoring_map = {}
        for commit in data.get("commits", []):
            for refactoring_data in commit.get("refactorings", []):
                if 'contextDescription' in refactoring_data:
                    refactoring = Refactoring(refactoring_data)
                    refactoring_map[refactoring.context_description + '\n' + remove_java_comments(refactoring.source_code_before)] = refactoring.to_dict()
        return refactoring_map

    def save_to_file(self, filename, format="json"):
        """将 refactoring_map 保存为 JSON 或 Pickle 文件。"""
        with open(filename, "w" if format == "json" else "wb") as f:
            if format == "json":
                json.dump(self.refactoring_map, f, indent=4)
            elif format == "pickle":
                pickle.dump(self.refactoring_map, f)

    @staticmethod
    def load_from_file(filename, format="json"):
        """从 JSON 或 Pickle 文件加载 refactoring_map。"""
        with open(filename, "r" if format == "json" else "rb") as f:
            return json.load(f) if format == "json" else pickle.load(f)

    def find_by_context_description(self, description):
        """通过 contextDescription 查找 refactoring。"""
        return self.refactoring_map.get(description, "Refactoring not found")


if __name__ == "__main__":
    file_path = 'data/refactoring_info/refactoring_miner_em_refactoring_context_w_sc_v2.json'
    with open(file_path, 'r') as file:
        data = json.load(file)
    # 初始化仓库对象
    repo = RefactoringRepository(data)

    # 保存到 JSON 文件
    repo.save_to_file("data/refactoring_info/refactoring_map_em_wc_v2.json", format="json")

    # 从 JSON 文件加载
    loaded_repo = RefactoringRepository.load_from_file("data/refactoring_info/refactoring_map_em_wc_v2.json", format="json")

    # 查找特定 contextDescription 的 refactoring
    description_to_search = "The `reset` method in the `KeyguardAbsKeyInputView` class is responsible for resetting the key input view to its initial state. It first clears any existing password text, checks if the user is currently locked out based on the lockout deadline, and either initiates a countdown for lockout or resets the state of the input view. This method interacts with other methods such as `resetPasswordText`, `handleAttemptLockout`, and `resetState`, which manage the user interface and security logic related to password entry and lockout conditions.\npublic void reset() {\n        // start fresh\n        resetPasswordText(false /* animate */);\n        // if the user is currently locked out, enforce it.\n        long deadline = mLockPatternUtils.getLockoutAttemptDeadline();\n        if (shouldLockout(deadline)) {\n            handleAttemptLockout(deadline);\n        } else {\n            resetState();\n        }\n    }"

    # 打印查找结果
    result = repo.find_by_context_description(description_to_search)
    print("Search Result:", result)
