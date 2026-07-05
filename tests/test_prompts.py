"""
Testes automatizados para validação de prompts.
"""
import re
import pytest
import yaml
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from utils import validate_prompt_structure

PROMPTS_FILE = Path(__file__).parent.parent / "prompts" / "bug_to_user_story_v2.yml"
PROMPT_KEY = "bug_to_user_story_v2"


def load_prompts(file_path: str):
    """Carrega prompts do arquivo YAML."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)


@pytest.fixture(scope="module")
def prompt_data():
    """Carrega o prompt otimizado v2 do arquivo YAML."""
    data = load_prompts(PROMPTS_FILE)
    assert data is not None, f"Arquivo YAML vazio ou inválido: {PROMPTS_FILE}"
    assert PROMPT_KEY in data, f"Chave '{PROMPT_KEY}' não encontrada em {PROMPTS_FILE}"
    return data[PROMPT_KEY]


class TestPrompts:
    def test_prompt_has_system_prompt(self, prompt_data):
        """Verifica se o campo 'system_prompt' existe e não está vazio."""
        assert "system_prompt" in prompt_data, "Campo 'system_prompt' não existe"
        assert prompt_data["system_prompt"].strip(), "Campo 'system_prompt' está vazio"

    def test_prompt_has_role_definition(self, prompt_data):
        """Verifica se o prompt define uma persona (ex: "Você é um Product Manager")."""
        system_prompt = prompt_data["system_prompt"]
        assert re.search(r"Você é um(a)?\s+\w+", system_prompt), (
            "Prompt não define uma persona (esperado algo como 'Você é um Product Manager')"
        )

    def test_prompt_mentions_format(self, prompt_data):
        """Verifica se o prompt exige formato Markdown ou User Story padrão."""
        system_prompt = prompt_data["system_prompt"].lower()
        assert "markdown" in system_prompt or "formato padrão" in system_prompt, (
            "Prompt não exige formato Markdown nem formato padrão de User Story"
        )
        assert "user story" in system_prompt, "Prompt não menciona User Story"

    def test_prompt_has_few_shot_examples(self, prompt_data):
        """Verifica se o prompt contém exemplos de entrada/saída (técnica Few-shot)."""
        system_prompt = prompt_data["system_prompt"]
        assert re.search(r"exemplo", system_prompt, re.IGNORECASE), (
            "Prompt não contém seção de exemplos"
        )
        # Exemplo completo = par entrada (Relato de Bug) / saída (User Story)
        assert "Relato de Bug:" in system_prompt, "Exemplos não mostram a entrada (relato de bug)"
        assert "Como um" in system_prompt and "Critérios de Aceitação" in system_prompt, (
            "Exemplos não mostram a saída esperada (user story com critérios)"
        )

    def test_prompt_no_todos(self, prompt_data):
        """Garante que você não esqueceu nenhum `[TODO]` no texto."""
        content = yaml.dump(prompt_data, allow_unicode=True)
        # Marcador literal [TODO] — substring "TODO" solta geraria falso positivo
        # em texto português ("TODOS", "TODO O FLUXO")
        assert "[TODO]" not in content, "Prompt ainda contém marcações [TODO]"

    def test_minimum_techniques(self, prompt_data):
        """Verifica (através dos metadados do yaml) se pelo menos 2 técnicas foram listadas."""
        techniques = prompt_data.get("techniques_applied", [])
        assert len(techniques) >= 2, (
            f"Mínimo de 2 técnicas requeridas, encontradas: {len(techniques)}"
        )
        # Reusa a validação oficial do projeto (exige description, version e >= 2 técnicas)
        is_valid, errors = validate_prompt_structure(prompt_data)
        assert is_valid, f"Estrutura do prompt inválida: {errors}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
