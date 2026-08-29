# --- GPT Input ---
# items_list_text (str):  "1. Code: 10 | Name: <ITEM_NAME> | Definition: <what this item means>\n2. Code: 20 | Name: ..."
# source_text (str):      "<the free-text input the model classifies against the provided items>"
#
# --- GPT Output (json.loads of response.choices[0].message.content) ---
# [{"code": 10, "name": "<exact name from list>", "score": 4}, {"code": 20, "name": "...", "score": 5}]
# Empty when no match: []

import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv
from openai import AzureOpenAI

from template_service.repositories.logging_repository import LoggingRepository

load_dotenv()


class GptFeatureNameRepository:

    client = AzureOpenAI(api_key=os.getenv("AZURE_OPENAI_API_KEY"), api_version=os.getenv("AZURE_OPENAI_API_VERSION"), azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"), http_client=httpx.Client(verify=False))

    @staticmethod
    def run_feature(items_list_text, source_text, flow_id):
        LoggingRepository.log_event(status="STARTING", content={"source_length": len(source_text)}, flow_id=flow_id, level="INFO")
        response_text = ""
        try:
            prompt_text = (Path(__file__).resolve().parents[3] / "project" / "src" / "prompts" / "gpt_feature_name_repository.md").read_text(encoding="utf-8")
            response = GptFeatureNameRepository.client.chat.completions.create(
                model=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
                seed=151,
                top_p=1,
                messages=[
                    {"role": "system",
                     "content": [
                         {
                             "type": "text",
                            "text": prompt_text
                         }
                     ]
                     },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps({"source": source_text, "provided_items": items_list_text}, ensure_ascii=False)
                            }
                        ]
                    }
                ]
            )
            response_text = response.choices[0].message.content
        except Exception as err:
            LoggingRepository.log_event(status="ERROR", content={"error": repr(err)}, flow_id=flow_id, level="ERROR")
        LoggingRepository.log_event(status="FINISHED", content={"response_length": len(response_text)}, flow_id=flow_id, level="INFO")
        return json.loads(response_text)
