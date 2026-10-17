import ipaddress
import os
import socket
import threading
import pygame

LARGURA, ALTURA = 160, 168
ESCALA = 4
TAM_BLOCO = 8          # tamanho de cada quadradinho, em pixels
COLUNAS, LINHAS = 10, 20
EFEITO_LCD = True      # grade fina por cima da tela, estilo game boy

PORTA = 13001          # porta padrão do servidor
TIMEOUT = 5            # tempo de timeout da conexão

# o jogo inteiro usa só essas 4 cores
ESCURO = (15, 56, 15)
MEDIO = (48, 98, 48)
CLARO = (139, 172, 15)
FUNDO = (155, 188, 15)


# função que usa a fonte pixelada se o arquivo estiver na pasta, senão usa a padrão do pygame
def carregar_fonte(tamanho):
    pasta = os.path.dirname(os.path.abspath(__file__))
    try:
        return pygame.font.Font(os.path.join(pasta, "PressStart2P-Regular.ttf"), tamanho)
    except FileNotFoundError:
        return pygame.font.Font(None, tamanho + 4)


pygame.init()
janela = pygame.display.set_mode((LARGURA * ESCALA, ALTURA * ESCALA))
pygame.display.set_caption("Tetris")
tela = pygame.Surface((LARGURA, ALTURA))  # tudo é desenhado aqui, não direto na janela
relogio = pygame.time.Clock()
fonte = carregar_fonte(8)
pygame.key.set_repeat(400, 40)  # segurar uma tecla faz ela repetir (ex: backspace)

estado = "menu"  # tela atual: "menu", "ip" ou "jogo"
rodando = True
tempo = 0.0      # tempo desde o início, usado pra fazer a tela piscar, dando o efeito de gameboy

OPCOES = ["JOGAR", "SAIR"]
selecionada = 0  # posição da opção marcada no menu

# letras do título feitas de blocos: cada # vira um bloquinho
LETRAS = {
    "T": ["###", ".#.", ".#.", ".#.", ".#."],
    "E": ["###", "#..", "##.", "#..", "###"],
    "R": ["##.", "#.#", "##.", "#.#", "#.#"],
    "I": ["###", ".#.", ".#.", ".#.", "###"],
    "S": [".##", "#..", ".#.", "..#", "##."],
    "P": ["##.", "#.#", "##.", "#..", "#.."],
}

# enfeite no rodapé do menu, cada X é um bloco
PILHA = [
    "XX    XXX    XX   X ",
    "XXX XXXXXXX XXXXX XX",
]

# caracteres que um campo de texto pode aceitar
LETRAS_NUMEROS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "
DIGITOS_IP = "0123456789."


# caixa onde o jogador digita (usada na tela do ip)
class CampoTexto:
    def __init__(self, x, y, limite=8, permitidos=LETRAS_NUMEROS):
        self.limite = limite
        self.permitidos = permitidos
        self.rect = pygame.Rect(x, y, limite * 8 + 8, 14)  # cada letra da fonte tem 8px
        self.texto = ""
        self.ativo = True  # se está recebendo o que é digitado

    def evento(self, evento):
        # retorna o texto quando aperta enter, senão retorna None
        if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
            pos = (evento.pos[0] // ESCALA, evento.pos[1] // ESCALA)
            self.ativo = self.rect.collidepoint(pos)  # clicar fora desativa
        elif not self.ativo:
            return None
        elif evento.type == pygame.TEXTINPUT:  # letra digitada
            for c in evento.text.upper():
                if c in self.permitidos and len(self.texto) < self.limite:
                    self.texto += c
        elif evento.type == pygame.KEYDOWN:  # teclas especiais
            if evento.key == pygame.K_BACKSPACE:
                self.texto = self.texto[:-1]
            elif evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                return self.texto.strip()
        return None

    def desenhar(self, tempo):
        pygame.draw.rect(tela, FUNDO, self.rect)
        pygame.draw.rect(tela, ESCURO if self.ativo else MEDIO, self.rect, 1)
        img = fonte.render(self.texto, False, ESCURO)
        tela.blit(img, (self.rect.x + 4, self.rect.y + 3))

        # cursor piscando logo depois da última letra
        if self.ativo and len(self.texto) < self.limite and int(tempo * 2) % 2 == 0:
            x = self.rect.x + 4 + img.get_width()
            pygame.draw.rect(tela, ESCURO, (x, self.rect.y + 3, 7, 7))


# escreve um texto na tela, por padrão centralizado no ponto pos
def escrever(texto, cor, pos, centralizado=True):
    img = fonte.render(texto, False, cor)  # False deixa a letra sem suavização
    rect = img.get_rect(center=pos) if centralizado else img.get_rect(topleft=pos)
    tela.blit(img, rect)


# bloco do tetris: borda escura, miolo da cor e um pixel claro de brilho
def desenhar_bloco(x, y, cor, tam=TAM_BLOCO):
    pygame.draw.rect(tela, ESCURO, (x, y, tam, tam))
    pygame.draw.rect(tela, cor, (x + 1, y + 1, tam - 2, tam - 2))
    pygame.draw.rect(tela, FUNDO, (x + 2, y + 2, 1, 1))


# desenha uma palavra usando as letras do dicionário LETRAS
def desenhar_titulo(texto, y, tam=6):
    x = (LARGURA - (len(texto) * 4 - 1) * tam) // 2  # cada letra ocupa 3 colunas + 1 de espaço
    for n, letra in enumerate(texto):
        cor = ESCURO if n % 2 == 0 else MEDIO  # alterna a cor entre as letras
        for lin, linha in enumerate(LETRAS[letra]):
            for col, c in enumerate(linha):
                if c == "#":
                    desenhar_bloco(x + col * tam, y + lin * tam, cor, tam)
        x += 4 * tam


# setinha do menu, desenhada uma linha de cada vez
def desenhar_seta(x, y):
    for i in range(7):
        pygame.draw.rect(tela, ESCURO, (x, y + i, 4 - abs(3 - i), 1))


# caixa com borda
def desenhar_moldura(rect, dupla=True):
    pygame.draw.rect(tela, FUNDO, rect)
    pygame.draw.rect(tela, ESCURO, rect, 1)
    if dupla:
        pygame.draw.rect(tela, ESCURO, rect.inflate(-4, -4), 1)


# tijolo das paredes em volta do tabuleiro
def desenhar_tijolo(x, y):
    pygame.draw.rect(tela, MEDIO, (x, y, 8, 8))
    pygame.draw.line(tela, ESCURO, (x, y + 3), (x + 7, y + 3))
    pygame.draw.line(tela, ESCURO, (x, y + 7), (x + 7, y + 7))
    pygame.draw.line(tela, ESCURO, (x + 5, y), (x + 5, y + 2))
    pygame.draw.line(tela, ESCURO, (x + 1, y + 4), (x + 1, y + 6))


# camada transparente com linhas finas, colocada por cima de tudo no final de cada frame
def criar_efeito_lcd():
    camada = pygame.Surface(janela.get_size(), pygame.SRCALPHA)
    cor = (*ESCURO, 30)
    for x in range(0, janela.get_width(), ESCALA):
        pygame.draw.line(camada, cor, (x, 0), (x, janela.get_height()))
    for y in range(0, janela.get_height(), ESCALA):
        pygame.draw.line(camada, cor, (0, y), (janela.get_width(), y))
    return camada


# confere se o texto é um ip válido, tipo 192.168.0.10
def ip_valido(texto):
    try:
        ipaddress.IPv4Address(texto)
        return True
    except ValueError:
        return False


conexao = None              # socket com o servidor, depois de conectar
conectando = False
status = "ENTER: CONECTAR"  # mensagem que aparece na tela do ip


# roda numa thread separada, assim a janela não trava enquanto espera o servidor
def conectar(ip):
    global conexao, conectando, status
    soquete = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    soquete.settimeout(TIMEOUT)  # desiste se o servidor demorar demais

    try:
        soquete.connect((ip, PORTA))
        soquete.settimeout(None)  # já conectou, tira o limite de tempo
        conexao = soquete
        status = "CONECTADO!"
    except ConnectionRefusedError:
        status = "CONEXAO RECUSADA"  # o pc existe, mas não tem servidor na porta
    except socket.timeout:
        status = "SEM RESPOSTA"      # ip errado, pc desligado ou firewall
    except OSError:
        status = "ERRO DE REDE"

    if conexao is None:  # deu errado: libera o campo pra tentar de novo
        soquete.close()
        campo.ativo = True
    conectando = False


efeito_lcd = criar_efeito_lcd()


# menu

# o que acontece quando o jogador confirma uma opção
def escolher(opcao):
    global estado, rodando, status
    if opcao == "JOGAR":
        estado = "ip"
        campo.ativo = True
        status = "ENTER: CONECTAR"
    elif opcao == "SAIR":
        rodando = False


# setas mudam a opção marcada, enter confirma
def eventos_menu(evento):
    global selecionada, tempo
    if evento.type != pygame.KEYDOWN:
        return
    if evento.key in (pygame.K_UP, pygame.K_w):
        selecionada = (selecionada - 1) % len(OPCOES)
        tempo = 0  # zera pra seta aparecer na hora
    elif evento.key in (pygame.K_DOWN, pygame.K_s):
        selecionada = (selecionada + 1) % len(OPCOES)
        tempo = 0
    elif evento.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
        escolher(OPCOES[selecionada])
    elif evento.key == pygame.K_ESCAPE:
        escolher("SAIR")


def desenhar_menu():
    tela.fill(FUNDO)
    desenhar_titulo("TETRIS", 16)

    desenhar_moldura(pygame.Rect(36, 76, 88, 46))
    for i, texto in enumerate(OPCOES):
        y = 87 + i * 16
        if i == selecionada:
            escrever(texto, ESCURO, (60, y), centralizado=False)
            if int(tempo * 3) % 2 == 0:  # seta piscando
                desenhar_seta(50, y)
        else:
            escrever(texto, MEDIO, (60, y), centralizado=False)

    escrever("SETAS + ENTER", MEDIO, (LARGURA // 2, 138))

    # monte de blocos no rodapé
    for lin, linha in enumerate(PILHA):
        for col, c in enumerate(linha):
            if c == "X":
                cor = MEDIO if (col // 2 + lin) % 2 == 0 else CLARO
                desenhar_bloco(col * TAM_BLOCO, ALTURA - (len(PILHA) - lin) * TAM_BLOCO, cor)


# tela do ip

campo = CampoTexto(0, 68, limite=15, permitidos=DIGITOS_IP)  # 15 cabe "255.255.255.255"
campo.rect.centerx = LARGURA // 2


def eventos_ip(evento):
    global estado, conectando, status
    if conectando:  # enquanto tenta conectar, ignora as teclas
        return
    if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
        estado = "menu"
        return

    ip = campo.evento(evento)
    if ip is None:  # ainda não apertou enter
        return
    if ip_valido(ip):
        conectando = True
        campo.ativo = False
        threading.Thread(target=conectar, args=(ip,), daemon=True).start()
    else:
        status = "IP INVALIDO"


# quando a thread terminar de conectar, vai pro jogo
def atualizar_ip():
    global estado
    if conexao is not None:
        estado = "jogo"


def desenha_ip():
    tela.fill(FUNDO)
    desenhar_titulo("IP", 16)
    escrever("DO SERVIDOR", ESCURO, (LARGURA // 2, 56))

    campo.desenhar(tempo)
    escrever(f"PORTA {PORTA}", MEDIO, (LARGURA // 2, 96))

    if conectando:
        pontos = "." * (int(tempo * 3) % 4)  # pontinhos animados
        escrever("CONECTANDO" + pontos.ljust(3), ESCURO, (LARGURA // 2, 120))
    else:
        escrever(status, ESCURO, (LARGURA // 2, 120))

    escrever("ESC: VOLTAR", MEDIO, (LARGURA // 2, 152))


# jogo

TABULEIRO = pygame.Rect(8, 0, COLUNAS * TAM_BLOCO, LINHAS * TAM_BLOCO)  # área onde as peças caem


def eventos_jogo(evento):
    global estado
    if evento.type == pygame.KEYDOWN and evento.key == pygame.K_ESCAPE:
        estado = "menu"
    # aqui vão os controles: mover, girar e hard drop


def atualizar_jogo(dt):
    pass  # aqui vai a lógica: queda da peça, colisão, limpar linhas


def desenhar_jogo():
    tela.fill(CLARO)

    # paredes e chão de tijolo em volta do tabuleiro
    pygame.draw.rect(tela, FUNDO, TABULEIRO)
    for y in range(0, ALTURA, TAM_BLOCO):
        desenhar_tijolo(0, y)
        desenhar_tijolo(TABULEIRO.right, y)
    for x in range(TABULEIRO.left, TABULEIRO.right, TAM_BLOCO):
        desenhar_tijolo(x, TABULEIRO.bottom)

    # texto provisório até o jogo ficar pronto
    escrever("SEU", MEDIO, (TABULEIRO.centerx, 70))
    escrever("TETRIS", MEDIO, (TABULEIRO.centerx, 80))
    escrever("AQUI", MEDIO, (TABULEIRO.centerx, 90))

    # painel do lado direito
    centro = (TABULEIRO.right + 8 + LARGURA) // 2
    desenhar_moldura(pygame.Rect(97, 4, 62, 26), dupla=False)
    escrever("PONTOS", ESCURO, (centro, 12))
    escrever("0", ESCURO, (centro, 22))
    desenhar_moldura(pygame.Rect(97, 36, 62, 44), dupla=False)
    escrever("PROXIMA", ESCURO, (centro, 44))
    desenhar_moldura(pygame.Rect(97, 86, 62, 26), dupla=False)
    escrever("NIVEL", ESCURO, (centro, 94))
    escrever("1", ESCURO, (centro, 104))
    escrever("ESC", ESCURO, (centro, 146))
    escrever("MENU", ESCURO, (centro, 156))


# loop principal: a cada frame trata os eventos, atualiza e desenha a tela atual
while rodando:
    dt = relogio.tick(60) / 1000  # segundos desde o último frame (limitado a 60 fps)
    tempo += dt

    # cada tela trata os próprios eventos
    for evento in pygame.event.get():
        if evento.type == pygame.QUIT:
            rodando = False
        elif estado == "menu":
            eventos_menu(evento)
        elif estado == "ip":
            eventos_ip(evento)
        elif estado == "jogo":
            eventos_jogo(evento)

    if estado == "menu":
        desenhar_menu()
    elif estado == "ip":
        atualizar_ip()
        desenha_ip()
    elif estado == "jogo":
        atualizar_jogo(dt)
        desenhar_jogo()

    # amplia a tela pequena pra janela sem suavizar, por isso fica pixelado
    pygame.transform.scale(tela, janela.get_size(), janela)
    if EFEITO_LCD:
        janela.blit(efeito_lcd, (0, 0))
    pygame.display.flip()

if conexao is not None:
    conexao.close()
pygame.quit()