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

    st.markdown("**Issues & PRs**")
    st.markdown("- Show me issues by label")
    st.markdown("- What PRs need review?")

    st.markdown("**GitHub Actions/CI/CD**")
    st.markdown("- Show all failed workflow runs")
    st.markdown("- Which workflows take longest?")
    st.markdown("- Analyze CI/CD success rates")

    st.markdown("**Code Search**")
    st.markdown("- Find TODO/FIXME comments")
    st.markdown("- Search for hardcoded secrets")
    st.markdown("- Find deprecated API usage")

    st.markdown("**Branch Analysis**")
    st.markdown("- List stale branches (>60 days)")
    st.markdown("- Compare main with develop branch")
    st.markdown("- Show unmerged feature branches")

    st.markdown("**Commits & Releases**")
    st.markdown("- Top contributors this month")
    st.markdown("- Generate changelog since last release")

    st.markdown("---")
    st.caption("💡 Tip: The agent now supports workflows, code search, branches, commits, and releases!")

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
        "Issues",
        "Pull Requests",
        "GitHub Actions/CI/CD",
        "Code Search",
        "Branch Analysis",
        "Commit History",
        "Releases",
        "Repository Activity",
        "Custom"
    ])

if query_type == "Issues":
    query_template = f"Find issues labeled as bugs in {repo}" if repo else "Find issues labeled as bugs"
elif query_type == "Pull Requests":
    query_template = f"Show me recent merged PRs in {repo}" if repo else "Show me recent merged PRs"
elif query_type == "GitHub Actions/CI/CD":
    query_template = f"Analyze workflow runs and identify any failures in {repo}" if repo else "Analyze workflow runs and identify any failures"
elif query_type == "Code Search":
    query_template = f"Search for TODO comments in {repo}" if repo else "Search for TODO comments"
elif query_type == "Branch Analysis":
    query_template = f"List all stale branches (no activity in 60 days) in {repo}" if repo else "List all stale branches"
elif query_type == "Commit History":
    query_template = f"Show commit patterns and top contributors in {repo}" if repo else "Show commit patterns and top contributors"
elif query_type == "Releases":
    query_template = f"Show recent releases and generate changelog in {repo}" if repo else "Show recent releases"
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
                "GITHUB_TOOLSETS": "repos,issues,pull_requests,workflows,search,branches,commits,releases"
            }
        )

        async with MCPTools(server_params=server_params) as mcp_tools:
            agent = Agent(
                tools=[mcp_tools],
                instructions=dedent("""\
                    You are an advanced GitHub intelligence agent with comprehensive repository analysis capabilities.

                    **Core Capabilities:**
                    - Repository analysis (structure, health, metrics, statistics)
                    - Issue & PR tracking with detailed insights
                    - GitHub Actions/CI/CD workflow analysis (runs, jobs, failures, performance)
                    - Code search across repositories (files, patterns, functions, security issues)
                    - Branch management (comparison, divergence, stale branches, protection rules)
                    - Commit history analysis (patterns, authors, file changes)
                    - Release tracking (versions, changelogs, frequency)

                    **GitHub Actions/Workflows Analysis:**
                    - Identify failing workflows and their failure patterns
                    - Analyze workflow run times and performance bottlenecks
                    - Track CI/CD success rates and trends
                    - Identify slow jobs and suggest optimizations
                    - Monitor deployment frequency and reliability

                    **Code Search Capabilities:**
                    - Search for specific code patterns, functions, or classes
                    - Find security vulnerabilities (hardcoded secrets, SQL injection risks)
                    - Locate deprecated API usage
                    - Track TODO/FIXME comments
                    - Find code duplication across files

                    **Branch Analysis:**
                    - Compare branches and show divergence
                    - Identify stale branches (no recent activity)
                    - Analyze branch protection rules
                    - Track branch creation and deletion patterns
                    - Find unmerged feature branches

                    **Analysis Guidelines:**
                    - Provide actionable insights, not just raw data
                    - Identify trends, patterns, and anomalies
                    - Highlight potential issues, bottlenecks, or risks
                    - Cross-reference related items (link PRs to issues, commits to workflows)
                    - Suggest improvements and optimizations when applicable

                    **Data Presentation:**
                    - Use markdown tables for comparative/structured data
                    - Use bullet points for lists and summaries
                    - Use code blocks for code snippets and file paths
                    - Include statistics, percentages, and trends
                    - Add emoji indicators (✅ success, ❌ failure, ⚠️ warning, 🔄 in-progress)
                    - Include clickable GitHub links to relevant pages

                    **Multi-Step Analysis:**
                    When appropriate, perform comprehensive analysis by:
                    1. Gathering data from multiple sources
                    2. Identifying patterns and correlations
                    3. Providing context and explanations
                    4. Offering recommendations

                    **Proactive Insights:**
                    - Flag failing workflows without being asked
                    - Identify security concerns in code
                    - Highlight stale PRs or branches
                    - Suggest workflow optimizations
                    - Point out unusual patterns or anomalies
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