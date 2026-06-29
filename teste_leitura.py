import os
import sys
from aws_conector import get_connection


def main():
    token = os.getenv('AWS_RDS_IAM_TOKEN') or os.getenv('RDS_IAM_TOKEN')
    conn = None
    try:
        conn = get_connection(
            auth_token=token,
            password=os.getenv('DB_PASSWORD') or os.getenv('RDS_PASSWORD'),
        )
        with conn.cursor() as cur:
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = [row['table_name'] for row in cur.fetchall()]
            print('Tabelas encontradas:')
            for table in tables:
                print('-', table)

            if 'macaco' in [t.lower() for t in tables]:
                cur.execute('SELECT id, nome, especie, idade FROM Macaco ORDER BY id;')
                rows = cur.fetchall()
                print('Dados da tabela Macaco:')
                for row in rows:
                    print(row)
            else:
                print('Tabela Macaco ainda não existe.')
    except Exception as e:
        print('Erro ao ler dados:', e)
        sys.exit(1)
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass


if __name__ == '__main__':
    main()
