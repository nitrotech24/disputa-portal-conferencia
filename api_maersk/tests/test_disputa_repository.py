import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from repos.disputa_repository import DisputaRepository

def main():
    repo = DisputaRepository()
    # exemplo: invoice_id=1, dispute_number=999999, status="New"
    repo.insert_or_update(invoice_id=1, dispute_number=999999, status="New")
    print("✅ Disputa inserida/atualizada com sucesso.")

if __name__ == "__main__":
    main()
