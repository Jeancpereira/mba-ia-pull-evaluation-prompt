"""
Script para fazer push de prompts otimizados ao LangSmith Prompt Hub.

Este script:
1. Lê os prompts otimizados de prompts/bug_to_user_story_v2.yml
2. Valida os prompts
3. Faz push PÚBLICO para o LangSmith Hub
4. Adiciona metadados (tags, descrição, técnicas utilizadas)

SIMPLIFICADO: Código mais limpo e direto ao ponto.
"""

import os
import sys
from dotenv import load_dotenv
from langsmith import Client
from langchain_core.prompts import ChatPromptTemplate
from utils import load_yaml, check_env_vars, print_section_header

load_dotenv()

PROMPTS_FILE = "prompts/bug_to_user_story_v2.yml"
PROMPT_KEY = "bug_to_user_story_v2"


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida estrutura básica de um prompt (versão simplificada).

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    errors = []

    for field in ["description", "system_prompt", "user_prompt", "version"]:
        if not str(prompt_data.get(field, "")).strip():
            errors.append(f"Campo obrigatório faltando ou vazio: {field}")

    system_prompt = prompt_data.get("system_prompt", "")
    if "TODO" in system_prompt:
        errors.append("system_prompt ainda contém TODOs")

    if "{bug_report}" not in prompt_data.get("user_prompt", ""):
        errors.append("user_prompt deve conter a variável {bug_report}")

    if "{bug_report}" in system_prompt:
        errors.append("system_prompt não deve duplicar a variável {bug_report}")

    techniques = prompt_data.get("techniques_applied", [])
    if len(techniques) < 2:
        errors.append(f"Mínimo de 2 técnicas requeridas, encontradas: {len(techniques)}")

    return (len(errors) == 0, errors)


def push_prompt_to_langsmith(prompt_name: str, prompt_data: dict) -> bool:
    """
    Faz push do prompt otimizado para o LangSmith Hub (PÚBLICO).

    Args:
        prompt_name: Nome do prompt
        prompt_data: Dados do prompt

    Returns:
        True se sucesso, False caso contrário
    """
    print(f"Validando prompt '{prompt_name}'...")

    is_valid, errors = validate_prompt(prompt_data)
    if not is_valid:
        print("❌ Prompt inválido:")
        for error in errors:
            print(f"   - {error}")
        return False

    print("   ✓ Prompt válido")

    prompt_template = ChatPromptTemplate.from_messages([
        ("system", prompt_data["system_prompt"]),
        ("user", prompt_data["user_prompt"]),
    ])

    techniques = prompt_data.get("techniques_applied", [])
    tags = prompt_data.get("tags", []) + techniques
    description = (
        f"{prompt_data['description']} "
        f"(versão {prompt_data['version']} | técnicas: {', '.join(techniques)})"
    )

    print(f"Publicando '{prompt_name}' no LangSmith Hub (público)...")

    try:
        client = Client()
        url = client.push_prompt(
            prompt_name,
            object=prompt_template,
            is_public=True,
            description=description,
            tags=tags,
        )
        print(f"   ✓ Prompt publicado com sucesso!")
        print(f"   URL: {url}")
        return True

    except Exception as e:
        print(f"❌ Erro ao publicar prompt: {e}")
        print("\nVerifique:")
        print("- LANGSMITH_API_KEY está configurada corretamente no .env")
        print("- Sua conta permite publicar prompts públicos no Hub")
        return False


def main():
    """Função principal"""
    print_section_header("PUSH DE PROMPTS OTIMIZADOS AO LANGSMITH HUB")

    if not check_env_vars(["LANGSMITH_API_KEY", "USERNAME_LANGSMITH_HUB"]):
        return 1

    data = load_yaml(PROMPTS_FILE)
    if not data or PROMPT_KEY not in data:
        print(f"❌ Prompt '{PROMPT_KEY}' não encontrado em {PROMPTS_FILE}")
        return 1

    if not push_prompt_to_langsmith(PROMPT_KEY, data[PROMPT_KEY]):
        return 1

    username = os.getenv("USERNAME_LANGSMITH_HUB")
    print("\n✅ Push concluído com sucesso!")
    print("\nPróximos passos:")
    print(f"1. Verifique no dashboard: https://smith.langchain.com/hub/{username}/{PROMPT_KEY}")
    print("2. Execute a avaliação: python src/evaluate.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
