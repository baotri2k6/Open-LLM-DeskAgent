import sys
import os

def import_global_mcp():
    # Find current dir and parent dir
    current_dir = os.path.abspath(os.path.dirname(__file__))
    parent_dir = os.path.abspath(os.path.join(current_dir, ".."))
    
    # Save sys.path
    saved_path = sys.path.copy()
    
    # Filter out local directories that might shadow the mcp library
    sys.path = [p for p in sys.path if os.path.abspath(p) not in (current_dir, parent_dir, "")]
    
    try:
        import mcp as global_mcp
        print("Successfully imported global mcp!")
        print("global_mcp path:", global_mcp.__file__)
        return global_mcp
    finally:
        sys.path = saved_path

if __name__ == "__main__":
    import_global_mcp()
