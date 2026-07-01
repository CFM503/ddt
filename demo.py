import asyncio
import os
import logging
from typing import Any
from dingtalk_client import DingTalkAITableClient

# Setup basic logging to see the connection flow
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("demo")

def safe_get(response: Any, key: str, default: Any = None) -> Any:
    """Helper to retrieve values from response dict, checking both root and 'data' key."""
    if not isinstance(response, dict):
        return default
    if key in response:
        return response[key]
    data = response.get("data")
    if isinstance(data, dict) and key in data:
        return data[key]
    return default

async def main():
    # 1. Retrieve the DingTalk MCP Server URL
    # You can set this as an environment variable or edit it directly here
    mcp_url = os.environ.get("DINGTALK_MCP_URL")
    
    if not mcp_url:
        logger.warning("DINGTALK_MCP_URL environment variable is not set.")
        # Prompts or uses a placeholder. Change this to your actual server url.
        mcp_url = "https://mcp.dingtalk.com/sse/..." 
        logger.info(f"Using default/placeholder URL: {mcp_url}")
        
    if "..." in mcp_url:
        print("\n" + "="*80)
        print("💡 QUICK START GUIDE:")
        print("Please set your DingTalk MCP URL before running this demo.")
        print("You can set it in your environment:")
        print("  Windows Powershell: $env:DINGTALK_MCP_URL=\"your-url\"")
        print("  Linux/Mac:          export DINGTALK_MCP_URL=\"your-url\"")
        print("Or edit demo.py directly to paste your URL.")
        print("="*80 + "\n")
        return

    logger.info("Starting DingTalk AI Table Demo...")

    # 2. Establish connection using context manager
    try:
        async with DingTalkAITableClient(mcp_url) as client:
            # --- 1. Select or Create Base ---
            base_id = os.environ.get("DINGTALK_BASE_ID")
            base_name = None
            base_detail = None

            if base_id:
                logger.info(f"Using DINGTALK_BASE_ID specified in environment: {base_id}")
                detail = await client.get_base(base_id=base_id)
                if safe_get(detail, "status") == "success":
                    base_detail = detail
                    base_name = safe_get(detail, "baseName", "User Specified Base")
                    logger.info(f"Successfully connected to specified base: '{base_name}'")
                else:
                    logger.warning(f"Specified base {base_id} is not accessible: {safe_get(detail, 'error')}")
                    base_id = None

            if not base_id:
                logger.info("No valid DINGTALK_BASE_ID provided. Scanning for existing 'test_demo_base'...")
                bases_response = await client.list_bases(limit=30)
                bases_list = safe_get(bases_response, "bases", [])
                
                # Look for a base named "test_demo_base" in list
                target_base = next((b for b in bases_list if b.get("baseName") == "test_demo_base"), None)
                
                if target_base:
                    test_id = target_base.get("baseId")
                    logger.info(f"Found existing 'test_demo_base' with ID: {test_id}. Testing accessibility...")
                    detail = await client.get_base(base_id=test_id)
                    if safe_get(detail, "status") == "success":
                        base_id = test_id
                        base_name = "test_demo_base"
                        base_detail = detail
                        logger.info("Successfully selected existing 'test_demo_base'")

            if not base_id:
                # If still not found, let's create a brand new base!
                logger.info("Existing 'test_demo_base' not found. Creating a brand new base named 'test_demo_base'...")
                create_base_res = await client.create_base(base_name="test_demo_base")
                logger.info(f"Create base response: {create_base_res}")
                
                base_id = safe_get(create_base_res, "baseId")
                if base_id:
                    logger.info(f"Successfully created base 'test_demo_base' with ID: {base_id}")
                    # Fetch base detail to populate tables info
                    base_detail = await client.get_base(base_id=base_id)
                    base_name = "test_demo_base"
                else:
                    logger.error("Failed to create new base 'test_demo_base'. Checking permission or quota.")
                    # Try to fall back to the first accessible base returned by list_bases
                    logger.info("Attempting fallback to find any accessible base...")
                    for base in bases_list:
                        test_id = base.get("baseId")
                        test_name = base.get("baseName")
                        logger.info(f"Testing fallback accessibility for base '{test_name}'...")
                        detail = await client.get_base(base_id=test_id)
                        if safe_get(detail, "status") == "success":
                            base_id = test_id
                            base_name = test_name
                            base_detail = detail
                            logger.info(f"Fallback selected base: '{base_name}'")
                            break
            
            if not base_id:
                logger.error("No writeable or accessible bases could be found or created in your account.")
                return
            
            # --- 2. Get Base Tables ---
            tables_list = safe_get(base_detail, "tables", [])
            # Check if "test_demo" already exists in the base
            existing_table = next((t for t in tables_list if t.get("tableName") == "test_demo"), None)
            
            if existing_table:
                table_id = existing_table.get("tableId")
                logger.info(f"Table 'test_demo' already exists with ID: {table_id}")
            else:
                # --- 3. Create 'test_demo' Table ---
                logger.info("Creating a new table named 'test_demo'...")
                fields = [
                    {"fieldName": "编号", "type": "text"},
                    {"fieldName": "图片附件", "type": "attachment"},
                    {"fieldName": "问题描述", "type": "text"},
                    {"fieldName": "责任人", "type": "user"}
                ]
                create_res = await client.create_table(base_id=base_id, table_name="test_demo", fields=fields)
                logger.info(f"Create table response: {create_res}")
                
                table_id = safe_get(create_res, "tableId")
                if table_id:
                    logger.info(f"Successfully created table 'test_demo' with ID: {table_id}")
                else:
                    # Try to find table if the response format is different
                    logger.warning("Could not parse tableId from create_table response. Checking base tables again...")
                    updated_base_detail = await client.get_base(base_id=base_id)
                    updated_tables = safe_get(updated_base_detail, "tables", [])
                    new_table = next((t for t in updated_tables if t.get("tableName") == "test_demo"), None)
                    if new_table:
                        table_id = new_table.get("tableId")
                        logger.info(f"Found newly created 'test_demo' table with ID: {table_id}")
                    else:
                        logger.error("Failed to verify creation of table 'test_demo'.")
                        return
            
            # --- 4. Get Table Details (Fields) ---
            logger.info(f"Fetching table structure for table '{table_id}'...")
            table_structure = await client.get_tables(base_id=base_id, table_ids=[table_id])
            logger.info(f"Table structure: {table_structure}")
            
            # --- 5. Query Records ---
            logger.info(f"Querying records in table 'test_demo'...")
            records_response = await client.query_records(base_id=base_id, table_id=table_id, limit=10)
            logger.info(f"Records response: {records_response}")
                
    except Exception as e:
        logger.exception("An error occurred while connecting or calling the MCP server:")

if __name__ == "__main__":
    asyncio.run(main())
