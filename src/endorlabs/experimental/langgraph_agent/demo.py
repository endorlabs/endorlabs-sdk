"""Demo entrypoint for the LangGraph Endor Labs agent.

Run with: uv run python -m endorlabs.experimental.langgraph_agent.demo

Env: ENDOR_API_CREDENTIALS_KEY, ENDOR_API_CREDENTIALS_SECRET, GEMINI_API_KEY (or .env).
"""

import os

from langchain_google_genai import ChatGoogleGenerativeAI

import endorlabs
from endorlabs.experimental.langgraph_agent import create_endor_graph


def main() -> None:
    #########################################################
    ## Initialize the Endor Labs client
    #########################################################
    client = endorlabs.Client(
        tenant="endor-solutions-tgowan",
        logging_level="ERROR",
        auth_method="api-key",
    )

    #########################################################
    ## Initialize the Google Gemini LLM
    #########################################################
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        api_key=os.getenv("GEMINI_API_KEY"),
    )

    #########################################################
    ## Create the Endor Labs agent graph
    #########################################################
    graph = create_endor_graph(client, llm)

    #########################################################
    ## Run the agent graph
    #########################################################
    result = graph.invoke(
        {
            "messages": [
                (
                    "user",
                    "Compare the last two or more Scan Logs to help"
                    " me troubleshoot scan errors for the"
                    " https://github.com/Endor-Solutions-Architecture"
                    "/endor-cockpit.git project",
                )
            ]
        }
    )
    print(result["messages"][-1].content)


if __name__ == "__main__":
    main()
