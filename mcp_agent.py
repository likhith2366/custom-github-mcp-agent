import asyncio
import os
import re
import subprocess
import streamlit as st
from textwrap import dedent
from typing import Optional, Tuple
from agno.agent import Agent
from agno.run.agent import RunOutput
from agno.tools.mcp import MCPTools
from mcp import StdioServerParameters

# Helper Functions
def validate_repo_format(repo: str) -> Tuple[bool, Optional[str]]:
    """
    Validate repository format (owner/repo).
    Returns (is_valid, error_message)
    """
    if not repo or not repo.strip():
        return False, "Repository cannot be empty"

    pattern = r'^[\w-]+/[\w.-]+$'
    if not re.match(pattern, repo):
        return False, "Repository must be in format 'owner/repo' (e.g., 'octocat/Hello-World')"

    return True, None


def check_docker_available() -> Tuple[bool, Optional[str]]:
    """
    Check if Docker is available and running.
    Returns (is_available, error_message)
    """
    try:
        result = subprocess.run(
            ['docker', 'ps'],
            capture_output=True,
            timeout=5,
            text=True
        )
        if result.returncode == 0:
            return True, None
        else:
            return False, "Docker is installed but not running. Please start Docker Desktop."
    except FileNotFoundError:
        return False, "Docker is not installed. Please install Docker Desktop from https://www.docker.com/products/docker-desktop"
    except subprocess.TimeoutExpired:
        return False, "Docker check timed out. Docker may be unresponsive."
    except Exception as e:
        return False, f"Error checking Docker: {str(e)}"


# Initialize session state
if 'openai_key' not in st.session_state:
    st.session_state.openai_key = ""
if 'github_token' not in st.session_state:
    st.session_state.github_token = ""
if 'docker_checked' not in st.session_state:
    st.session_state.docker_checked = False
if 'docker_available' not in st.session_state:
    st.session_state.docker_available = False

st.set_page_config(page_title="🐙 GitHub MCP Agent", page_icon="🐙", layout="wide")

st.markdown("<h1 class='main-header'>🐙 GitHub MCP Agent</h1>", unsafe_allow_html=True)
st.markdown("Explore GitHub repositories with natural language using the Model Context Protocol")

with st.sidebar:
    st.header("🔑 Authentication")

    openai_key = st.text_input(
        "OpenAI API Key",
        type="password",
        value=st.session_state.openai_key,
        help="Required for the AI agent to interpret queries and format results"
    )
    if openai_key:
        st.session_state.openai_key = openai_key
        os.environ["OPENAI_API_KEY"] = openai_key

    github_token = st.text_input(
        "GitHub Token",
        type="password",
        value=st.session_state.github_token,
        help="Create a token with repo scope at github.com/settings/tokens"
    )
    if github_token:
        st.session_state.github_token = github_token
        os.environ["GITHUB_TOKEN"] = github_token

    # Docker status check
    if not st.session_state.docker_checked:
        with st.spinner("Checking Docker availability..."):
            st.session_state.docker_available, docker_error = check_docker_available()
            st.session_state.docker_checked = True

    if st.session_state.docker_available:
        st.success("✓ Docker is running")
    else:
        docker_available, docker_error = check_docker_available()
        if not docker_available:
            st.error(f"✗ Docker: {docker_error}")
        else:
            st.session_state.docker_available = True
            st.success("✓ Docker is running")
    
    st.markdown("---")
    st.markdown("### Example Queries")
    
    st.markdown("**Issues**")
    st.markdown("- Show me issues by label")
    st.markdown("- What issues are being actively discussed?")
    
    st.markdown("**Pull Requests**")
    st.markdown("- What PRs need review?")
    st.markdown("- Show me recent merged PRs")
    
    st.markdown("**Repository**")
    st.markdown("- Show repository health metrics")
    st.markdown("- Show repository activity patterns")
    
    st.markdown("---")
    st.caption("Note: Always specify the repository in your query if not already selected in the main input.")

col1, col2 = st.columns([3, 1])
with col1:
    repo = st.text_input(
        "Repository",
        value="",
        placeholder="e.g., owner/repo",
        help="Format: owner/repo"
    )
    # Validate repository format
    if repo:
        is_valid, error_msg = validate_repo_format(repo)
        if not is_valid:
            st.error(error_msg)
with col2:
    query_type = st.selectbox("Query Type", [
        "Issues", "Pull Requests", "Repository Activity", "Custom"
    ])

if query_type == "Issues":
    query_template = f"Find issues labeled as bugs in {repo}" if repo else "Find issues labeled as bugs"
elif query_type == "Pull Requests":
    query_template = f"Show me recent merged PRs in {repo}" if repo else "Show me recent merged PRs"
elif query_type == "Repository Activity":
    query_template = f"Analyze code quality trends in {repo}" if repo else "Analyze code quality trends"
else:
    query_template = ""

query = st.text_area("Your Query", value=query_template, 
                     placeholder="What would you like to know about this repository?")

async def run_github_agent(message: str) -> str:
    """
    Run the GitHub agent with the given query message.
    Returns the agent's response or an error message.
    """
    if not os.getenv("GITHUB_TOKEN"):
        return "❌ Error: GitHub token not provided. Please enter your token in the sidebar."

    if not os.getenv("OPENAI_API_KEY"):
        return "❌ Error: OpenAI API key not provided. Please enter your API key in the sidebar."

    try:
        server_params = StdioServerParameters(
            command="docker",
            args=[
                "run", "-i", "--rm",
                "-e", "GITHUB_PERSONAL_ACCESS_TOKEN",
                "-e", "GITHUB_TOOLSETS",
                "ghcr.io/github/github-mcp-server"
            ],
            env={
                **os.environ,
                "GITHUB_PERSONAL_ACCESS_TOKEN": os.getenv('GITHUB_TOKEN'),
                "GITHUB_TOOLSETS": "repos,issues,pull_requests"
            }
        )

        async with MCPTools(server_params=server_params) as mcp_tools:
            agent = Agent(
                tools=[mcp_tools],
                instructions=dedent("""\
                    You are a GitHub assistant. Help users explore repositories and their activity.
                    - Provide organized, concise insights about the repository
                    - Focus on facts and data from the GitHub API
                    - Use markdown formatting for better readability
                    - Present numerical data in tables when appropriate
                    - Include links to relevant GitHub pages when helpful
                """),
                markdown=True,
            )

            response: RunOutput = await asyncio.wait_for(agent.arun(message), timeout=120.0)
            return response.content

    except asyncio.TimeoutError:
        return "⏱️ Error: Request timed out after 120 seconds. Try a simpler query or check your connection."
    except ConnectionError as e:
        return f"🔌 Error: Connection failed. Please check your internet connection.\nDetails: {str(e)}"
    except FileNotFoundError:
        return "🐳 Error: Docker command not found. Please ensure Docker is installed and in your PATH."
    except PermissionError as e:
        return f"🔒 Error: Permission denied. Docker may need elevated privileges.\nDetails: {str(e)}"
    except ValueError as e:
        return f"⚠️ Error: Invalid configuration or parameters.\nDetails: {str(e)}"
    except KeyError as e:
        return f"🔑 Error: Missing required configuration.\nDetails: {str(e)}"
    except Exception as e:
        error_type = type(e).__name__
        return f"❌ Unexpected error ({error_type}): {str(e)}\n\nPlease check:\n- Docker is running\n- Your tokens are valid\n- The repository exists and is accessible"

if st.button("🚀 Run Query", type="primary", use_container_width=True):
    # Validation checks
    if not openai_key:
        st.error("❌ Please enter your OpenAI API key in the sidebar")
    elif not github_token:
        st.error("❌ Please enter your GitHub token in the sidebar")
    elif not st.session_state.docker_available:
        st.error("❌ Docker is not available. Please ensure Docker is installed and running.")
    elif not query:
        st.error("❌ Please enter a query")
    elif repo:
        # Validate repository format if provided
        is_valid, error_msg = validate_repo_format(repo)
        if not is_valid:
            st.error(f"❌ Invalid repository format: {error_msg}")
        else:
            # Run the query
            with st.spinner("🔍 Analyzing GitHub repository..."):
                if repo and repo not in query:
                    full_query = f"{query} in {repo}"
                else:
                    full_query = query

                # Use asyncio.run instead of deprecated get_event_loop
                result = asyncio.run(run_github_agent(full_query))

            st.markdown("### 📊 Results")
            st.markdown(result)
    else:
        # Query without specific repo
        with st.spinner("🔍 Processing query..."):
            result = asyncio.run(run_github_agent(query))

        st.markdown("### 📊 Results")
        st.markdown(result)

if 'result' not in locals():
    st.markdown(
        """<div class='info-box'>
        <h4>How to use this app:</h4>
        <ol>
            <li>Enter your <strong>OpenAI API key</strong> in the sidebar (powers the AI agent)</li>
            <li>Enter your <strong>GitHub token</strong> in the sidebar</li>
            <li>Specify a repository (e.g., ikhith2366/lv-portfolio)</li>
            <li>Select a query type or write your own</li>
            <li>Click 'Run Query' to see results</li>
        </ol>
        <p><strong>How it works:</strong></p>
        <ul>
            <li>Uses the official GitHub MCP server via Docker for real-time access to GitHub API</li>
            <li>AI Agent (powered by OpenAI) interprets your queries and calls appropriate GitHub APIs</li>
            <li>Results are formatted in readable markdown with insights and links</li>
            <li>Queries work best when focused on specific aspects like issues, PRs, or repository info</li>
        </ul>
        </div>""", 
        unsafe_allow_html=True
    )