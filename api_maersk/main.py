@"


"""
API Maersk - Sistema de Gestão de Disputas
Ponto de entrada principal da aplicação
"""
import sys
from services.token_service import TokenService
from services.auth_service import AuthService
from services.dispute_service import DisputeService
from services.dispute_sync_service import DisputeSyncService
from repos.invoice_repository import InvoiceRepository
from repos.disputa_repository import DisputaRepository
from utils.logger import setup_logger

logger = setup_logger(__name__)


def exibir_menu():
    print("=" * 80)
    print("API MAERSK - GESTÃO DE DISPUTAS")
    print("=" * 80)
    print()
    print("1 - Sincronizar disputas de um cliente")
    print("2 - Sincronizar todos os clientes")
    print("3 - Renovar tokens")
    print("4 - Importar invoices faltantes")
    print("5 - Atualizar status de uma disputa")
    print("0 - Sair")
    print("=" * 80)


def main():
    token_service = TokenService()
    auth_service = AuthService(token_service)
    dispute_service = DisputeService(token_service, auth_service)
    invoice_repo = InvoiceRepository()
    disputa_repo = DisputaRepository()
    sync_service = DisputeSyncService(dispute_service, invoice_repo, disputa_repo)

    while True:
        exibir_menu()
        opcao = input("\nEscolha uma opção: ").strip()

        if opcao == "1":
            customer_code = input("Código do cliente: ").strip()
            limite = input("Limite de invoices (Enter para 1000): ").strip()
            limite = int(limite) if limite else 1000

            logger.info(f"Iniciando sincronização para {customer_code}")
            stats = sync_service.sync_disputes(customer_code, limit=limite)

            print()
            print("Resultado:")
            print(f"  Total processadas: {stats.get('total_invoices', 0)}")
            print(f"  Com disputa: {stats.get('com_disputa', 0)}")
            print(f"  Disputas salvas: {stats.get('disputas_salvas', 0)}")

        elif opcao == "2":
            print("Importando módulo...")
            from scripts.sync_all_customers import sync_all_customers
            sync_all_customers()

        elif opcao == "3":
            print("Renovando tokens...")
            auth_service.refresh_all_tokens()

        elif opcao == "4":
            print("Importando módulo...")
            from scripts.import_missing_invoices import main as import_main
            import_main()

        elif opcao == "5":
            customer_code = input("Código do cliente: ").strip()
            dispute_id = input("ID da disputa: ").strip()

            resultado = sync_service.update_dispute_status(dispute_id, customer_code)

            if resultado.get('success'):
                print(f"\nDisputa {dispute_id} atualizada com sucesso!")
                print(f"  Status: {resultado.get('status')}")
                print(f"  Invoice: {resultado.get('invoice_number')}")
            else:
                print(f"\nErro: {resultado.get('error')}")

        elif opcao == "0":
            print("\nEncerrando...")
            sys.exit(0)

        else:
            print("\nOpção inválida!")

        input("\nPressione Enter para continuar...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nPrograma interrompido pelo usuário")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        sys.exit(1)
"@ | Out-File -FilePath main.py -Encoding utf8