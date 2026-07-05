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
import string
import sys
from dotenv import load_dotenv
from langsmith import Client
from langchain_core.prompts import ChatPromptTemplate
from utils import load_yaml, check_env_vars, print_section_header, validate_prompt_structure

load_dotenv()

PROMPTS_FILE = "prompts/bug_to_user_story_v2.yml"
PROMPT_KEY = "bug_to_user_story_v2"


def extract_template_variables(text: str) -> set:
    """
    Extrai nomes de variáveis de template ({var}) de um texto.

    Args:
        text: Texto a analisar

    Returns:
        Conjunto de nomes de variáveis encontradas

    Raises:
        ValueError: Se o texto contiver chaves desbalanceadas
    """
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def validate_prompt(prompt_data: dict) -> tuple[bool, list]:
    """
    Valida um prompt para publicação: estrutura básica (compartilhada com os
    testes via utils.validate_prompt_structure) + regras de template.

    Args:
        prompt_data: Dados do prompt

    Returns:
        (is_valid, errors) - Tupla com status e lista de erros
    """
    _, errors = validate_prompt_structure(prompt_data)

    if not str(prompt_data.get("user_prompt", "")).strip():
        errors.append("Campo obrigatório faltando ou vazio: user_prompt")

    # O ChatPromptTemplate (f-string) transforma qualquer {x} literal em variável
    # obrigatória, que quebraria o evaluate.py (só fornece bug_report).
    try:
        system_vars = extract_template_variables(prompt_data.get("system_prompt", ""))
        user_vars = extract_template_variables(prompt_data.get("user_prompt", ""))
    except ValueError as e:
        errors.append(f"Chaves desbalanceadas no prompt: {e}")
        return (False, errors)

    if system_vars:
        errors.append(
            f"system_prompt não pode conter variáveis de template, encontradas: {sorted(system_vars)}"
        )

    if user_vars != {"bug_report"}:
        errors.append(
            f"user_prompt deve conter exatamente a variável {{bug_report}}, encontradas: {sorted(user_vars)}"
        )

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

    techniques = prompt_data.get("techniques_applied") or []
    tags = (prompt_data.get("tags") or []) + techniques
    description = (
        f"{prompt_data['description']} "
        f"(versão {prompt_data['version']} | técnicas: {', '.join(techniques)})"
    )

    print(f"Publicando '{prompt_name}' no LangSmith Hub (público)...")

    try:
        client = Client()

        # O evaluate.py puxa o prompt como {USERNAME_LANGSMITH_HUB}/{prompt_name}.
        # Se o username configurado não bater com o handle real da conta, o push
        # funcionaria mas a avaliação falharia com 404 — melhor falhar aqui.
        username = os.getenv("USERNAME_LANGSMITH_HUB", "")
        tenant_handle = getattr(client._get_settings(), "tenant_handle", None)

        if not tenant_handle:
            print("❌ Sua conta LangSmith ainda não tem um handle público do Hub.")
            print("   Crie um publicando qualquer prompt público pela UI: https://smith.langchain.com/prompts")
            return False

        if username != tenant_handle:
            print(f"❌ USERNAME_LANGSMITH_HUB ('{username}') difere do handle real da conta ('{tenant_handle}').")
            print("   Corrija o .env para que o evaluate.py encontre o prompt publicado.")
            return False

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
        if "Nothing to commit" in str(e):
            print("   ✓ Prompt já publicado e sem mudanças desde o último push")
            return True

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
