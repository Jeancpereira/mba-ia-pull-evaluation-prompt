"""
Script para fazer pull de prompts do LangSmith Prompt Hub.

Este script:
1. Conecta ao LangSmith usando credenciais do .env
2. Faz pull dos prompts do Hub
3. Salva localmente em prompts/bug_to_user_story_v1.yml

SIMPLIFICADO: Usa serialização nativa do LangChain para extrair prompts.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from langchain import hub
from utils import save_yaml, check_env_vars, print_section_header

load_dotenv()

SOURCE_PROMPT = "leonanluppi/bug_to_user_story_v1"
OUTPUT_FILE = "prompts/bug_to_user_story_v1.yml"


def extract_messages(prompt_template) -> dict:
    """
    Extrai system_prompt e user_prompt de um ChatPromptTemplate.

    Args:
        prompt_template: ChatPromptTemplate retornado pelo hub.pull

    Returns:
        Dicionário com system_prompt e user_prompt
    """
    system_prompt = ""
    user_prompt = ""

    for message in prompt_template.messages:
        template = getattr(getattr(message, "prompt", None), "template", "")
        role = type(message).__name__

        if "System" in role:
            system_prompt = template
        elif "Human" in role:
            user_prompt = template

    return {"system_prompt": system_prompt, "user_prompt": user_prompt}


def pull_prompts_from_langsmith():
    """
    Faz pull do prompt v1 do LangSmith Hub e salva em YAML local.

    Returns:
        True se sucesso, False caso contrário
    """
    print(f"Puxando prompt do LangSmith Hub: {SOURCE_PROMPT}")

    try:
        prompt_template = hub.pull(SOURCE_PROMPT)
    except Exception as e:
        print(f"❌ Erro ao puxar prompt '{SOURCE_PROMPT}': {e}")
        print("\nVerifique:")
        print("- LANGSMITH_API_KEY está configurada corretamente no .env")
        print("- O prompt existe e é público no LangSmith Hub")
        return False

    print("   ✓ Prompt carregado com sucesso")

    messages = extract_messages(prompt_template)

    if not messages["system_prompt"] and not messages["user_prompt"]:
        print("❌ Não foi possível extrair mensagens do prompt")
        return False

    prompt_data = {
        "bug_to_user_story_v1": {
            "description": "Prompt para converter relatos de bugs em User Stories",
            "system_prompt": messages["system_prompt"],
            "user_prompt": messages["user_prompt"],
            "version": "v1",
            "source": SOURCE_PROMPT,
            "tags": ["bug-analysis", "user-story", "product-management"],
        }
    }

    if not save_yaml(prompt_data, OUTPUT_FILE):
        return False

    print(f"   ✓ Prompt salvo em: {OUTPUT_FILE}")
    return True


def main():
    """Função principal"""
    print_section_header("PULL DE PROMPTS DO LANGSMITH HUB")

    if not check_env_vars(["LANGSMITH_API_KEY"]):
        return 1

    if not pull_prompts_from_langsmith():
        return 1

    print("\n✅ Pull concluído com sucesso!")
    print("\nPróximos passos:")
    print(f"1. Analise o prompt em {OUTPUT_FILE}")
    print("2. Crie sua versão otimizada em prompts/bug_to_user_story_v2.yml")
    print("3. Faça push: python src/push_prompts.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
