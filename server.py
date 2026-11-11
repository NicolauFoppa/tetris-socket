import socket
import threading
import random

HOST = '0.0.0.0'  # escuta em todas as interfaces de rede
PORTA = 13001

clientes = []
lock = threading.Lock()

def broadcast(mensagem, remetente=None):
    # envia a mensagem para todos os clientes (ou só para o oponente se remetente for informado).
    with lock:
        para_remover = []
        for c in clientes:
            if c != remetente:
                try:
                    c.sendall(f"{mensagem}\n".encode('utf-8'))
                except OSError:
                    para_remover.append(c)
        for c in para_remover:
            if c in clientes:
                clientes.remove(c)
                c.close()

def tratar_cliente(conexao, endereco, id_jogador):
    # thread dedicada a cada cliente para escutar mensagens e repassar
    print(f"[CONECTADO] Jogador {id_jogador} vindo de {endereco}")
    buffer = ""
    try:
        while True:
            dados = conexao.recv(1024).decode('utf-8')
            if not dados:
                break
            buffer += dados
            while "\n" in buffer:
                mensagem, buffer = buffer.split("\n", 1)
                mensagem = mensagem.strip()
                if not mensagem:
                    continue

                print(f"[JOGADOR {id_jogador}]: {mensagem}")
                # retransmite dados da partida para o oponente
                broadcast(mensagem, remetente=conexao)

    except (ConnectionResetError, OSError):
        pass
    finally:
        print(f"[DESCONECTADO] Jogador {id_jogador} saiu.")
        with lock:
            if conexao in clientes:
                clientes.remove(conexao)
        conexao.close()
        broadcast("OPONENTE_SAIU")

def iniciar_servidor():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        servidor.bind((HOST, PORTA))
        servidor.listen(2)
        print(f"=== SERVIDOR TETRIS SOCKETS RODANDO NA PORTA {PORTA} ===")

        while True:
            print("\n[AGUARDANDO] Esperando 2 jogadores se conectarem...")

            with lock:
                clientes.clear()

            # aceita exatamente 2 clientes
            while len(clientes) < 2:
                conexao, endereco = servidor.accept()
                with lock:
                    clientes.append(conexao)
                    id_jogador = len(clientes)
                
                print(f"[CONEXÃO ACCEPTED] Jogador {id_jogador}/2 conectado!")
                threading.Thread(target=tratar_cliente, args=(conexao, endereco, id_jogador), daemon=True).start()

            print("\n[SALA CHEIA] 2 jogadores na sala! Gerando seed sincronizada...")
            
            # semente única gerada pelo servidor
            seed = random.randint(100000, 999999)
            broadcast(f"START:{seed}")
            print(f"[SEED ENVIADA]: {seed}\n")

            # mantém o loop preso até alguém cair
            while True:
                with lock:
                    if len(clientes) < 2:
                        print("[PARTIDA FINALIZADA] Um jogador desconectou.")
                        break
                threading.Event().wait(1)

    except Exception as e:
        print(f"[ERRO SERVIDOR]: {e}")
    finally:
        servidor.close()

if __name__ == "__main__":
    iniciar_servidor()