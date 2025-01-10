from notion_client import Client
from todoist_api_python.api import TodoistAPI
import time

def fetch_existing_todoist_tasks(todoist):
    """
    Fetch all tasks from Todoist and extract associated Notion task IDs from their descriptions.
    """
    existing_tasks = {}
    try:
        tasks = todoist.get_tasks()
        for task in tasks:
            # Check if the description contains a Notion task ID (e.g., "NotionID: task_id")
            if task.description and task.description.startswith("NotionID:"):
                notion_id = task.description.split("NotionID:")[-1].strip()
                existing_tasks[notion_id] = task.id
    except Exception as e:
        print(f"Error fetching Todoist tasks: {e}")
    return existing_tasks

def create_todoist_task(todoist, project_id, notion_task_id, title, due_date, priority, task_labels, description, parent_id):
    # Create task in Todoist
    task = todoist.add_task(
        project_id=project_id,
        content=title,
        due_date=due_date if due_date else None,
        priority=priority,
        labels=task_labels,
        description=description,
        parent_id=parent_id
    )
    print(f"✓ Created Todoist task {notion_task_id} with Parent Id {parent_id}: {title}, {due_date}, {priority} with the filter(s) {task_labels}")
    return task.id

def check_page_hierarchy(properties): #This function checks if the notion task is a standalone task or a parent task
    try:
        parent_info = properties.get("Parent item")
        if parent_info.get("relation") == []:
            return True
        else:
            return False
    except Exception as e:
        return False

def getParentId(is_task_parent, notion_properties, existing_tasks): #This function fetches the todoist parent id of the task
    try:
        if is_task_parent:
            return None
        else:
            parent_info = notion_properties.get("Parent item")
            key = parent_info.get("relation")[0]["id"]
            return existing_tasks[key]
    except Exception as e:
        return None

def sync_notion_to_todoist(notion_token, todoist_token, database_id, project_id):
    """
    Sync Notion tasks to Todoist, avoiding duplicates by checking existing tasks.
    """
    # Initialize API clients
    notion = Client(auth=notion_token)
    todoist = TodoistAPI(todoist_token)
    
    # Fetch existing Todoist tasks
    existing_tasks = fetch_existing_todoist_tasks(todoist)
    print(f"Found {len(existing_tasks)} existing tasks in Todoist.")
    
    # Get all tasks from Notion database
    try:
        results = notion.databases.query(database_id=database_id)
        results['results'].reverse() # This is to reverse the order of the tasks so that the parent task is created first
        print(f"Found {len(results['results'])} tasks in Notion.")
        
        # Process each task
        for page in results["results"]:
            try:
                notion_task_id = page["id"]
                
                if notion_task_id in existing_tasks:
                    continue  # Skip tasks that are already in Todoist
                
                try:
                    notion_properties = page["properties"]
                    is_task_parent= check_page_hierarchy(notion_properties)
                except Exception as e:
                    print(f"Error extracting task details: {e}")
                    is_task_parent = False
                    
            
                # Extract task details from Notion
                title = page["properties"]["Name of Task"]["title"][0]["text"]["content"] # Change "Name of Task" to the name of the column in your notion database
                print(f"Processing task {notion_task_id} - {title}...")
                
                try:
                    #This is where you add the various columns in your notion database. The below is just an example
                    date_property = page["properties"].get("Deadline", {}).get("date", {}).get("end", "start")
                    select_property = page["properties"].get("Priority", {}).get("select", {}).get("name", 1)
                    multi_select_property = page["properties"].get("Task", {}).get("multi_select", [])
                except Exception as e:
                    print(f"Error extracting task details: {e}")
                    
                # Add Notion task ID to the description
                description = f"NotionID: {notion_task_id}"
                
                #create a task in todoist
                create_todoist_task(todoist, project_id, notion_task_id, title, date_property, select_property, multi_select_property, description, parent_id=getParentId(is_task_parent, notion_properties, existing_tasks))
                
                #update the existing tasks
                existing_tasks = fetch_existing_todoist_tasks(todoist)
                
                time.sleep(1)  # Avoid rate limiting
            except Exception as e:
                print(f"✗ Error processing task: {e}")
        
    except Exception as e:
        print(f"Error accessing Notion database: {e}")

if __name__ == "__main__":
    # Your API credentials
    NOTION_TOKEN = "YOUR_NOTION_TOKEN"
    TODOIST_TOKEN = "YOUR_TODOIST_TOKEN"
    DATABASE_ID = "YOUR_DATABASE_ID"
    PROJECT_ID= "YOUR_PROJECT_ID" # Can leave it as none if you want
    
    #Run the sync
    print(f"Syncing {DATABASE_ID}...")
    sync_notion_to_todoist(NOTION_TOKEN, TODOIST_TOKEN, DATABASE_ID, PROJECT_ID)
    
    print("Sync complete!")