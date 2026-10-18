import socket
import threading
import random

HOST = '0.0.0.0'  # escuta em todas as interfaces de rede
PORTA = 13001

clientes = []
lock = threading.Lock()

def tratar_cliente(conexao, endereco, id_jogador):
    """
    Thread responsável por ouvir um cliente específico e 
    retransmitir suas mensagens para o oponente.
    """
    print(f"[CONECTADO] Jogador {id_jogador} vindo de {endereco}")

    try:
        buffer = ""
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

                # identifica quem é o oponente
                oponente = None
                with lock:
                    for c in clientes:
                        if c != conexao:
                            oponente = c
                            break

                # retransmite a mensagem para o oponente
                if oponente:
                    try:
                        oponente.sendall(f"{mensagem}\n".encode('utf-8'))
                    except OSError:
                        pass

    except (ConnectionResetError, OSError):
        pass
    finally:
        print(f"[DESCONECTADO] Jogador {id_jogador} saiu.")
        with lock:
            if conexao in clientes:
                clientes.remove(conexao)
        conexao.close()


def iniciar_servidor():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        servidor.bind((HOST, PORTA))
        servidor.listen(2)
        print(f"=== SERVIDOR TETRIS SOCKETS RODANDO NA PORTA {PORTA} ===")
        print("Aguardando 2 jogadores se conectarem...\n")

        while True:
            # limpa conexões antigas se o servidor reiniciar a sala
            with lock:
                clientes.clear()

            # aguarda até ter 2 jogadores conectados
            while len(clientes) < 2:
                conexao, endereco = servidor.accept()
                with lock:
                    clientes.append(conexao)
                    id_jogador = len(clientes)
                
                print(f"Jogador {id_jogador}/2 conectado!")
                threading.Thread(target=tratar_cliente, args=(conexao, endereco, id_jogador), daemon=True).start()

            print("\n[SALA CHEIA] 2 jogadores conectados. Iniciando a partida!")
            
            # gera a semente inicial para sincronizar as peças
            seed = random.randint(100000, 999999)
            mensagem_inicio = f"START:{seed}\n"

            #envia a semente para ambos os clientes
            with lock:
                for c in clientes:
                    try:
                        c.sendall(mensagem_inicio.encode('utf-8'))
                    except OSError:
                        pass

            print(f"[SEED ENVIADA]: {seed}\n")

            # aguarda enquanto o jogo estiver acontecendo
            while True:
                with lock:
                    if len(clientes) < 2:
                        print("[PARTIDA ENCERRADA] Um dos jogadores caiu. Aguardando novos jogadores...\n")
                        break

    except Exception as e:
        print(f"[ERRO SERVIDOR]: {e}")
    finally:
        servidor.close()


if __name__ == "__main__":
    iniciar_servidor()