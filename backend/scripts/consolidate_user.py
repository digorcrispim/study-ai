"""
Script para consolidar todos os dados de usuários no ID fixo.

Executar UMA VEZ após o deploy do ID fixo.

Uso:
    cd ~/Projetos/study-ai
    backend/venv/bin/python backend/scripts/consolidate_user.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import create_engine, text

from backend.models.database import DATABASE_URL

FIXED_USER_ID = "da01e100-0001-0000-0000-000000000001"


def consolidate():
    engine = create_engine(DATABASE_URL)

    with engine.begin() as conn:
        # 1. Descobrir todos os user_ids distintos (exceto o fixo)
        result = conn.execute(text("""
            SELECT DISTINCT user_id FROM learning_plans
            WHERE user_id != :fixed_id
        """), {"fixed_id": FIXED_USER_ID})

        other_user_ids = [row[0] for row in result]

        if not other_user_ids:
            print("Nenhum usuario adicional encontrado. Nada a consolidar.")
            return

        print(f"Encontrados {len(other_user_ids)} usuario(s) adicional(is):")
        for uid in other_user_ids:
            print(f"   - {uid}")

        # 2. Para cada user_id, migrar dados para o ID fixo
        for old_id in other_user_ids:
            print(f"\nMigrando {old_id} -> {FIXED_USER_ID}...")

            # Migrar learning_plans (e items via cascade)
            conn.execute(text("""
                UPDATE learning_plans
                SET user_id = :new_id
                WHERE user_id = :old_id
            """), {"new_id": FIXED_USER_ID, "old_id": old_id})

            # Migrar study_sessions
            conn.execute(text("""
                UPDATE study_sessions
                SET user_id = :new_id
                WHERE user_id = :old_id
            """), {"new_id": FIXED_USER_ID, "old_id": old_id})

            # Migrar user_answers
            conn.execute(text("""
                UPDATE user_answers
                SET user_id = :new_id
                WHERE user_id = :old_id
            """), {"new_id": FIXED_USER_ID, "old_id": old_id})

            print(f"   {old_id} migrado com sucesso")

        # 3. Verificar resultado
        result = conn.execute(text("""
            SELECT COUNT(*) FROM learning_plans WHERE user_id = :fixed_id
        """), {"fixed_id": FIXED_USER_ID})
        total_plans = result.scalar()

        print(f"\nConsolidacao concluida!")
        print(f"   Total de planos do usuario fixo: {total_plans}")


if __name__ == "__main__":
    print("Iniciando consolidacao de usuarios...")
    print(f"   ID fixo: {FIXED_USER_ID}\n")
    consolidate()
