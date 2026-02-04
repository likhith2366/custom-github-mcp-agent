# GitHub MCP Agent

A Streamlit-based application that lets you explore GitHub repositories using natural language queries powered by the Model Context Protocol (MCP) and AI agents.

## Overview

This application combines the power of OpenAI's language models with GitHub's Model Context Protocol server to provide an intelligent interface for analyzing repositories, issues, pull requests, and repository activity patterns through natural language queries.

## Features

- **Natural Language Queries**: Ask questions about repositories in plain English
- **Multiple Query Types**: Pre-configured templates for common queries about issues, PRs, and repository activity
- **Real-time GitHub Data**: Direct access to GitHub API through the official GitHub MCP server
- **AI-Powered Insights**: OpenAI-powered agent interprets queries and formats results intelligently
- **Markdown Formatting**: Results presented in clean, readable markdown with tables and links
- **Comprehensive Repository Analysis**: Analyze issues, pull requests, code quality trends, and repository health

## Prerequisites

Before running this application, ensure you have:

- Python 3.8 or higher
- Docker installed and running (required for GitHub MCP server)
- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))
- GitHub Personal Access Token with `repo` scope ([Create one here](https://github.com/settings/tokens))

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/likhith2366/custom-github-mcp-agent.git
   cd custom-github-mcp-agent
   ```

2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Ensure Docker is running on your system:
   ```bash
   docker --version
   ```

## Usage

1. Start the Streamlit application:
   ```bash
   streamlit run mcp_agent.py
   ```

2. Open your browser and navigate to the URL shown (typically `http://localhost:8501`)

3. Configure your credentials in the sidebar:
   - Enter your **OpenAI API Key**
   - Enter your **GitHub Token**

4. Specify a repository in the format `owner/repo` (e.g., `likhith2366/lv-portfolio`)

5. Choose a query type or write your own custom query

6. Click **Run Query** to get AI-powered insights

## Example Queries

### Issues
- "Show me issues labeled as bugs"
- "Find issues labeled as bugs in {repo}"
- "What issues are being actively discussed?"
- "List all open issues with high priority"

### Pull Requests
- "Show me recent merged PRs"
- "What PRs need review?"
- "Display pull requests by a specific author"

### Repository Activity
- "Show repository health metrics"
- "Analyze code quality trends"
- "Show repository activity patterns"
- "What are the most active files?"

## How It Works

1. **GitHub MCP Server**: Runs in a Docker container providing access to GitHub API through the Model Context Protocol
2. **AI Agent**: Uses OpenAI's language models (via the Agno library) to interpret queries and call appropriate GitHub APIs
3. **Streamlit Interface**: Provides an intuitive web interface for entering queries and viewing results
4. **Formatted Results**: AI agent processes raw GitHub data and presents it as organized, readable markdown

## Architecture

```
User Query → Streamlit UI → Agno Agent → MCP Tools → GitHub MCP Server (Docker) → GitHub API
                                ↓
                          OpenAI API (Query Understanding)
                                ↓
                          Formatted Results
```

## Requirements

- `streamlit>=1.28.0` - Web application framework
- `agno>=2.2.10` - AI agent framework
- `mcp>=1.26.0` - Model Context Protocol implementation
- `PyGithub>=1.55` - GitHub API wrapper

See [requirements.txt](requirements.txt) for full dependency list.

## Configuration

### Environment Variables

The application uses the following environment variables (set through the UI):
- `OPENAI_API_KEY` - Your OpenAI API key
- `GITHUB_TOKEN` - Your GitHub Personal Access Token

### GitHub MCP Server Configuration

The application configures the GitHub MCP server with these toolsets:
- `repos` - Repository information and metrics
- `issues` - Issue tracking and management
- `pull_requests` - Pull request analysis

## Troubleshooting

### Docker Connection Issues
- Ensure Docker Desktop is running
- Verify Docker is accessible from command line: `docker ps`

### Timeout Errors
- Queries timeout after 120 seconds
- Try breaking complex queries into smaller ones

### Authentication Errors
- Verify your GitHub token has `repo` scope
- Check that your OpenAI API key is valid and has available credits

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Acknowledgments

- Built with [Streamlit](https://streamlit.io/)
- Powered by [OpenAI](https://openai.com/)
- Uses [GitHub MCP Server](https://github.com/github/github-mcp-server)
- Agent framework by [Agno](https://github.com/agno-agi/agno)

## Author

**likhith2366**

## Support

If you encounter any issues or have questions, please file an issue on the [GitHub repository](https://github.com/likhith2366/custom-github-mcp-agent/issues).
