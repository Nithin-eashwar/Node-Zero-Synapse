import os
import json
from tree_sitter_languages import get_language, get_parser

# --- CONFIGURATION ---
REPO_PATH = "./dummy_repo"  # Point this to your folder
OUTPUT_FILE = "repo_graph.json"

# --- 1. SETUP PARSER ---
language = get_language("python")
parser = get_parser("python")

# --- 2. DATA STRUCTURE ---
class CodeEntity:
    def __init__(self, name, file_path, start_line, end_line):
        self.name = name
        self.file_path = file_path
        self.start_line = start_line
        self.end_line = end_line
        self.calls = []

    def to_dict(self):
        return {
            "name": self.name,
            "file": self.file_path,
            "range": [self.start_line, self.end_line],
            "calls": self.calls
        }

# --- 3. PARSING LOGIC (Reuse from before) ---
def find_calls(node):
    calls = []
    if node.type == "call":
        function_name_node = node.child_by_field_name("function")
        if function_name_node:
            calls.append(function_name_node.text.decode("utf8"))
    for child in node.children:
        calls.extend(find_calls(child))
    return calls

def parse_file(file_path):
    with open(file_path, "r", encoding="utf8") as f:
        code = f.read()
    
    tree = parser.parse(bytes(code, "utf8"))
    root_node = tree.root_node
    
    entities = []
    
    for node in root_node.children:
        if node.type == "function_definition":
            name_node = node.child_by_field_name("name")
            func_name = name_node.text.decode("utf8")
            
            entity = CodeEntity(
                func_name, 
                file_path,
                node.start_point[0], 
                node.end_point[0]
            )
            
            body_node = node.child_by_field_name("body")
            entity.calls = find_calls(body_node)
            entities.append(entity)
            
    return entities

# --- 4. MAIN WALKER ---
def scan_repository(path):
    print(f"🚀 Scanning Repository: {path}...")
    all_functions = []
    
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                print(f"  -> Parsing {file}...")
                try:
                    file_entities = parse_file(full_path)
                    all_functions.extend(file_entities)
                except Exception as e:
                    print(f"  ❌ Error parsing {file}: {e}")

    return all_functions

# --- 5. EXECUTION ---
if __name__ == "__main__":
    if not os.path.exists(REPO_PATH):
        print(f"❌ Error: The folder '{REPO_PATH}' does not exist.")
        print("Please create 'dummy_repo' with some python files first.")
    else:
        results = scan_repository(REPO_PATH)
        
        # Save to JSON
        with open(OUTPUT_FILE, "w") as f:
            json.dump([e.to_dict() for e in results], f, indent=2)
            
        print(f"\n✅ Success! Scanned {len(results)} functions.")
        print(f"💾 Database saved to: {OUTPUT_FILE}")