import sys
import os

# Create dummy local mcp in sys.modules to simulate being imported
class DummyLocalMcp:
    pass

sys.modules['mcp'] = DummyLocalMcp()

# Now try the import trick
def import_global_mcp_advanced():
    _cur_dir = os.path.dirname(os.path.abspath(__file__))
    _parent_dir = os.path.dirname(_cur_dir)
    
    # Save sys.path and sys.modules
    _saved_paths = sys.path.copy()
    local_mcp = sys.modules.pop('mcp', None)
    
    # Remove local paths from sys.path
    sys.path = [p for p in sys.path if os.path.abspath(p) not in (_cur_dir, _parent_dir, "")]
    
    try:
        # Import the global mcp library
        import mcp as global_mcp
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        print("Successfully imported global components:")
        print("ClientSession:", ClientSession)
        print("stdio_client:", stdio_client)
    except Exception as e:
        print("Import failed:", e)
    finally:
        # Restore sys.path and local mcp module
        sys.path = _saved_paths
        if local_mcp is not None:
            sys.modules['mcp'] = local_mcp

if __name__ == "__main__":
    import_global_mcp_advanced()
    # Check if local mcp was restored
    print("Restored sys.modules['mcp']:", sys.modules.get('mcp'))
