import os
import autogen
import chainlit as cl
from chainlit_agents import ChainlitUserProxyAgent, ChainlitAssistantAgent
import psycopg2  # Or your preferred PostgreSQL library (e.g., asyncpg)
from typing import List, Dict
from dotenv import load_dotenv

load_dotenv()

# --- Database Connection (Replace with your actual credentials) ---
DB_HOST = os.getenv('DB_HOST')
DB_NAME = os.getenv('DB_NAME')
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')

def get_db_connection():
    conn = psycopg2.connect(host=DB_HOST, database=DB_NAME, user=DB_USER, password=DB_PASSWORD)
    return conn

# --- Helper functions ---
def create_project(user_id: int, project_name: str, description: str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO projects (user_id, project_name, description) VALUES (%s, %s, %s) RETURNING project_id;",
        (user_id, project_name, description),
    )
    project_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return project_id

def create_task(project_id: int, task_name: str, description: str, assigned_agent: str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO tasks (project_id, task_name, description, assigned_agent) VALUES (%s, %s, %s, %s) RETURNING task_id;",
        (project_id, task_name, description, assigned_agent),
    )
    task_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return task_id

def log_interaction(task_id: int, agent_definition_id: int, message: str, interaction_type: str, metadata: Dict):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO task_interactions (task_id, agent_definition_id, message, interaction_type, metadata) VALUES (%s, %s, %s, %s, %s);",
        (task_id, agent_definition_id, message, interaction_type, metadata),
    )
    conn.commit()
    cur.close()
    conn.close()

def get_agent_definition(agent_name: str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT agent_definition_id, system_message, llm_config FROM agent_definitions WHERE agent_name = %s;", (agent_name,))
    result = cur.fetchone()
    cur.close()
    conn.close()
    if result:
      agent_definition_id, system_message, llm_config = result
      return {"id": agent_definition_id, "system_message": system_message, "llm_config": llm_config}
    else:
      return None

def create_user(username:str, email:str, password_hash:str, is_paid:bool):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO users (username, email, password_hash, is_paid) VALUES (%s, %s, %s, %s) RETURNING user_id;",
        (username, email, password_hash, is_paid),
    )
    user_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return user_id

def get_user(username:str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE username = %s;", (username,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user

def add_feedback(user_id: int, task_id: int, feedback_text: str):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO feedback (user_id, task_id, feedback_text) VALUES (%s, %s, %s);", (user_id, task_id, feedback_text))
    conn.commit()
    cur.close()
    conn.close()


# --- Autogen Setup ---
api_key = os.getenv('API_KEY')
config_list_openai = [
    {"model": "gpt-4o", "api_key": api_key}
]
llm_config = {
    "seed": 221,
    "temperature": 0,
    "config_list": config_list_openai,
    "timeout": 60000,
}

# --- Agent System Messages (Placeholders - Refine these!) ---
USER_PROXY_MESSAGE = "Admin: Interface with the user.  Relay user requests, collect feedback, and manage the overall project.  Always ask for clarification if the user's request is ambiguous."
ENGINEER_MESSAGE = "Engineer: Specialize in structural analysis and design.  Use FEA tools and principles to solve problems. Always provide clear explanations for your decisions."
PLANNER_MESSAGE = "Planner: Manage the task workflow, delegate tasks to appropriate agents, and ensure efficient collaboration. Break down complex problems into smaller, manageable sub-tasks."
SCIENTIST_MESSAGE = "Scientist: Analyze data, interpret results, and provide insights. Use statistical methods and visualization tools to communicate findings."
EXECUTOR_MESSAGE = "Executor: Execute code, run simulations, and interact with external tools (e.g., CAD software, FEA solvers).  Report results and any errors encountered."
CRITIC_MESSAGE = "Critic: Evaluate the work of other agents, identify potential flaws, and suggest improvements.  Focus on accuracy, efficiency, and adherence to best practices."


@cl.on_chat_start
async def on_chat_start():
  try:
    print("Set agents.")
        # Check if user exists, if not create a new one
    username = cl.user_session.get("user_name")
    if not username:
        # Prompt the user for their username
        username = await cl.AskUserMessage(content="Please enter a username:").send()
        while not username or not username["output"].strip():
              username = await cl.AskUserMessage(content="Username cannot be empty. Please enter a valid username:").send()

        username = username['output'].strip()
        cl.user_session.set("user_name", username)


    user = get_user(username)
    if not user:
        # You'll need a secure way to handle passwords in a real app!
        password_hash = "placeholder_password" # NEVER DO THIS IN PRODUCTION
        email = f"{username}@example.com" # Placeholder email
        user_id = create_user(username, email, password_hash, False) # Initially not paid
    else:
        user_id = user[0] # user_id is the first element in the returned tuple
    cl.user_session.set("user_id", user_id)


    # Load agent definitions from the database
    engineer_def = get_agent_definition("Engineer")
    scientist_def = get_agent_definition("Scientist")
    planner_def = get_agent_definition("Planner")
    critic_def = get_agent_definition("Critic")
    executor_def = get_agent_definition("Executor")

    user_proxy  = ChainlitUserProxyAgent("Admin", system_message=USER_PROXY_MESSAGE, code_execution_config=False)
    engineer    = ChainlitAssistantAgent("Engineer", llm_config=engineer_def["llm_config"], system_message=engineer_def["system_message"])
    scientist   = ChainlitAssistantAgent("Scientist", llm_config=scientist_def["llm_config"], system_message=scientist_def["system_message"])
    planner     = ChainlitAssistantAgent("Planner", llm_config=planner_def["llm_config"], system_message=planner_def["system_message"])
    critic      = ChainlitAssistantAgent("Critic", llm_config=critic_def["llm_config"], system_message=critic_def["system_message"])
    executor    = ChainlitAssistantAgent("Executor", system_message=executor_def["system_message"], human_input_mode="NEVER",
                                     code_execution_config={"last_n_messages": 3, "work_dir": "FEA_results","use_docker": False})

    cl.user_session.set("user_proxy", user_proxy)
    cl.user_session.set("engineer", engineer)
    cl.user_session.set("scientist", scientist)
    cl.user_session.set("planner", planner)
    cl.user_session.set("critic", critic)
    cl.user_session.set("executor", executor)


    msg = cl.Message(content="Welcome to the AI-powered engineering assistant! What project would you like to start?", author="User_Proxy")
    await msg.send()

  except Exception as e:
    print("Error: ", e)
    pass

@cl.on_message
async def run_conversation(message: cl.Message):
    MAX_ITER = 50
    CONTEXT = message.content
    user_id = cl.user_session.get("user_id")

    user_proxy = cl.user_session.get("user_proxy")
    planner = cl.user_session.get("planner")
    engineer = cl.user_session.get("engineer")
    critic = cl.user_session.get("critic")
    executor = cl.user_session.get("executor")
    scientist = cl.user_session.get("scientist")

    # --- Project and Task Initialization ---
    if not cl.user_session.get("current_project_id"):
      project_name = await cl.AskUserMessage(content="Please enter a name for your new project:").send()
      project_name = project_name['output'].strip()
      project_description = await cl.AskUserMessage(content="Please provide a brief description of the project:").send()
      project_description = project_description['output'].strip()
      project_id = create_project(user_id, project_name, project_description)
      cl.user_session.set("current_project_id", project_id)
      await cl.Message(content=f"Created project: {project_name} (ID: {project_id})").send()

    project_id = cl.user_session.get("current_project_id")
    task_name = CONTEXT  # Use the user's message as the initial task name
    task_description = "Initial task generated from user input." # Provide an initial description.
    task_id = create_task(project_id, task_name, task_description, "Planner")  # Initially assign to the Planner

    # --- Agent Interaction and Logging ---
    groupchat = autogen.GroupChat(
        agents=[user_proxy, planner, engineer, scientist, executor, critic],
        messages=[],
        max_round=MAX_ITER,
    )
    manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=llm_config)

    print("Running conversation")

    async def initiate_chat_and_log(*args, **kwargs):
      await cl.make_async(user_proxy.initiate_chat)(*args, **kwargs)

      # Log interactions after each agent turn (This is a simplified example)
      for message in groupchat.messages:
          sender_name = message["name"]
          agent_def = get_agent_definition(sender_name)
          if agent_def:
              agent_definition_id = agent_def["id"]
              interaction_type = "output" if sender_name != "Admin" else "input"
              metadata = {}  # Add any relevant metadata here
              log_interaction(task_id, agent_definition_id, message["content"], interaction_type, metadata)

    await initiate_chat_and_log(manager, message=CONTEXT)

    # --- Collect Feedback ---
    feedback = await cl.AskUserMessage(content="Please provide feedback on this interaction:").send()
    if feedback and feedback['output'].strip():
        add_feedback(user_id, task_id, feedback['output'].strip())
        await cl.Message(content="Thank you for your feedback!").send()