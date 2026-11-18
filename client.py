import ipaddress
import os
import random
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

#Formatos das pecas
S = [['.....',
      '.....',
      '..00.',
      '.00..',
      '.....'],
     ['.....',
      '..0..',
      '..00.',
      '...0.',
      '.....']]

Z = [['.....',
      '.....',
      '.00..',
      '..00.',
      '.....'],
     ['.....',
      '..0..',
      '.00..',
      '.0...',
      '.....']]

I = [['.....',
      '..0..',
      '..0..',
      '..0..',
      '..0..'],
     ['.....',
      '0000.',
      '.....',
      '.....',
      '.....']]

O = [['.....',
      '.....',
      '.00..',
      '.00..',
      '.....']]

J = [['.....',
      '.0...',
      '.000.',
      '.....',
      '.....'],
     ['.....',
      '..00.',
      '..0..',
      '..0..',
      '.....'],
     ['.....',
      '.....',
      '.000.',
      '...0.',
      '.....'],
     ['.....',
      '..0..',
      '..0..',
      '.00..',
      '.....']]

L = [['.....',
      '...0.',
      '.000.',
      '.....',
      '.....'],
     ['.....',
      '..0..',
      '..0..',
      '..00.',
      '.....'],
     ['.....',
      '.....',
      '.000.',
      '.0...',
      '.....'],
     ['.....',
      '.00..',
      '..0..',
      '..0..',
      '.....']]

T = [['.....',
      '..0..',
      '.000.',
      '.....',
      '.....'],
     ['.....',
      '..0..',
      '..00.',
      '..0..',
      '.....'],
     ['.....',
      '.....',
      '.000.',
      '..0..',
      '.....'],
     ['.....',
      '..0..',
      '.00..',
      '..0..',
      '.....']]

# index represents the shape
shapes = [S, Z, I, O, J, L, T]
CORES_PECAS = [MEDIO, ESCURO, CLARO, MEDIO, ESCURO, CLARO, MEDIO]  # cor de cada formato, na mesma ordem


# função que usa a fonte pixelada se o arquivo estiver na pasta, senão usa a padrão do pygame
def carregar_fonte(tamanho):
    pasta = os.path.dirname(os.path.abspath(__file__))
    try:
        return pygame.font.Font(os.path.join(pasta, "PressStart2P-Regular.ttf"), tamanho)
    except FileNotFoundError:
        return pygame.font.Font(None, tamanho + 4)


JOGADORES = 2
MARGEM_X = (LARGURA * JOGADORES - LARGURA) // 2  # onde o menu e a tela do ip ficam, centralizados no quadro

pygame.init()
janela = pygame.display.set_mode((LARGURA * JOGADORES * ESCALA, ALTURA * ESCALA))
pygame.display.set_caption("Tetris")
tela = pygame.Surface((LARGURA, ALTURA))  # cada tela/tabuleiro é desenhado aqui, não direto na janela
quadro = pygame.Surface((LARGURA * JOGADORES, ALTURA))  # junta tudo lado a lado antes de ampliar pra janela
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
            pos = (evento.pos[0] // ESCALA - MARGEM_X, evento.pos[1] // ESCALA)
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

class Peca(object):
    def __init__(self, x, y, shape):
        self.x = x
        self.y = y
        self.shape = shape
        self.rotation = 0
        self.cor = CORES_PECAS[shapes.index(shape)]


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


def convert_shape_format(piece):
    positions = []
    shape_format = piece.shape[piece.rotation % len(piece.shape)]

    for i, line in enumerate(shape_format):
        row = list(line)
        for j, column in enumerate(row):
            if column == '0':
                positions.append((piece.x + j, piece.y + i))

    for i, pos in enumerate(positions):
        positions[i] = (pos[0] - 2, pos[1] -4)
    return positions

# a peça pode ficar ali? acima do tabuleiro (y < 0) pode, desde que não saia pelos lados
def valid_space(piece, grid):
    for x, y in convert_shape_format(piece):
        if x < 0 or x >= COLUNAS or y >= LINHAS:
            return False
        if y >= 0 and grid[y][x] is not None:
            return False
    return True


# monta a grade 10x20: None é vazio, senão guarda a cor do bloco fixado
def criar_grade(travadas):
    grade = [[None for _ in range(COLUNAS)] for _ in range(LINHAS)]
    for (x, y), cor in travadas.items():
        grade[y][x] = cor
    return grade


# apaga as linhas cheias e desce o que estava em cima, retorna quantas apagou
def limpar_linhas(grade, travadas):
    cheias = [y for y in range(LINHAS) if None not in grade[y]]
    if not cheias:
        return 0

    novas = {}
    for (x, y), cor in travadas.items():
        if y in cheias:
            continue
        desce = sum(1 for c in cheias if c > y)  # quantas linhas cheias tinha embaixo dele
        novas[(x, y + desce)] = cor
    travadas.clear()
    travadas.update(novas)
    return len(cheias)



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
        iniciar_partida()


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
PONTOS_LINHAS = [0, 40, 100, 300, 1200]  # pontos por apagar 1, 2, 3 ou 4 linhas de uma vez

# teclas de cada jogador
TECLAS_P1 = {"esq": pygame.K_a, "dir": pygame.K_d, "girar": pygame.K_w,
             "desce": pygame.K_s, "drop": pygame.K_SPACE}
TECLAS_P2 = {"esq": pygame.K_LEFT, "dir": pygame.K_RIGHT, "girar": pygame.K_UP,
             "desce": pygame.K_DOWN, "drop": pygame.K_RETURN}


# tudo de um tabuleiro: cada jogador tem o seu
class Jogo:
    def __init__(self, nome, teclas):
        self.nome = nome
        self.teclas = teclas
        self.gerador = random.Random()  # sorteia as peças; com a mesma seed os dois recebem a mesma sequência
        self.iniciar()

    # zera tudo pra começar uma partida
    def iniciar(self, seed=None):
        self.gerador.seed(seed)
        self.travadas = {}           # (x, y) -> cor dos blocos já fixados
        self.grade = criar_grade(self.travadas)
        self.peca_atual = self.nova_peca()
        self.proxima_peca = self.nova_peca()
        self.pontos = 0
        self.linhas_feitas = 0
        self.timer_queda = 0.0       # tempo acumulado desde a última vez que a peça desceu
        self.fim_de_jogo = False

    def nova_peca(self):
        return Peca(5, 2, self.gerador.choice(shapes))

    def nivel(self):
        return self.linhas_feitas // 10

    # segundos entre cada descida automática, fica mais rápido a cada nível
    def intervalo_queda(self):
        return max(0.1, 0.8 - self.nivel() * 0.07)

    # tenta mover a peça; se não couber, desfaz e retorna False
    def mover(self, dx, dy, giro=0):
        peca = self.peca_atual
        peca.x += dx
        peca.y += dy
        peca.rotation += giro
        if valid_space(peca, self.grade):
            return True
        peca.x -= dx
        peca.y -= dy
        peca.rotation -= giro
        return False

    # fixa a peça no tabuleiro, apaga linhas e puxa a próxima
    def travar_peca(self):
        for x, y in convert_shape_format(self.peca_atual):
            if y < 0:  # travou com pedaço pra fora do topo
                self.fim_de_jogo = True
            else:
                self.travadas[(x, y)] = self.peca_atual.cor
        self.grade = criar_grade(self.travadas)

        apagadas = limpar_linhas(self.grade, self.travadas)
        if apagadas:
            self.pontos += PONTOS_LINHAS[apagadas] * (self.nivel() + 1)
            self.linhas_feitas += apagadas
            self.grade = criar_grade(self.travadas)

        self.peca_atual, self.proxima_peca = self.proxima_peca, self.nova_peca()
        if not valid_space(self.peca_atual, self.grade):  # não tem espaço nem pra nascer
            self.fim_de_jogo = True

    # trata uma tecla apertada, se ela for desse jogador
    def tecla(self, tecla):
        if tecla == self.teclas["esq"]:
            self.mover(-1, 0)
        elif tecla == self.teclas["dir"]:
            self.mover(1, 0)
        elif tecla == self.teclas["girar"]:
            self.mover(0, 0, giro=1)
        elif tecla == self.teclas["desce"]:  # soft drop
            if not self.mover(0, 1):
                self.travar_peca()
            self.timer_queda = 0
        elif tecla == self.teclas["drop"]:  # hard drop: desce até encostar e já trava
            while self.mover(0, 1):
                pass
            self.travar_peca()
            self.timer_queda = 0

    def atualizar(self, dt):
        self.timer_queda += dt
        if self.timer_queda >= self.intervalo_queda():
            self.timer_queda = 0
            if not self.mover(0, 1):
                self.travar_peca()


jogos = [Jogo("P1", TECLAS_P1), Jogo("P2", TECLAS_P2)]
tempo_jogo = 0.0  # segundos desde o início da partida


# começa a partida dos dois com a mesma seed (depois ela vai vir do servidor, no START:seed)
def iniciar_partida(seed=None):
    global tempo_jogo
    if seed is None:
        seed = random.randint(100000, 999999)
    for jogo in jogos:
        jogo.iniciar(seed)
    tempo_jogo = 0.0


# a partida acaba quando qualquer um dos dois perde
def partida_acabou():
    return any(jogo.fim_de_jogo for jogo in jogos)


def eventos_jogo(evento):
    global estado
    if evento.type != pygame.KEYDOWN:
        return
    if evento.key == pygame.K_ESCAPE:
        estado = "menu"
    elif partida_acabou():
        if evento.key == pygame.K_r:
            iniciar_partida()
    else:
        for jogo in jogos:
            jogo.tecla(evento.key)


def atualizar_jogo(dt):
    global tempo_jogo
    if partida_acabou():
        return
    tempo_jogo += dt
    for jogo in jogos:
        jogo.atualizar(dt)


# desenha a próxima peça centralizada dentro da caixa
def desenhar_proxima(proxima_peca, rect, tam=6):
    formato = proxima_peca.shape[0]
    blocos = [(j, i) for i, linha in enumerate(formato) for j, c in enumerate(linha) if c == '0']
    min_x = min(j for j, _ in blocos)
    min_y = min(i for _, i in blocos)
    largura = (max(j for j, _ in blocos) - min_x + 1) * tam
    altura = (max(i for _, i in blocos) - min_y + 1) * tam
    x0 = rect.centerx - largura // 2
    y0 = rect.centery - altura // 2
    for j, i in blocos:
        desenhar_bloco(x0 + (j - min_x) * tam, y0 + (i - min_y) * tam, proxima_peca.cor, tam)


def desenhar_jogo(jogo):
    tela.fill(CLARO)

    # paredes e chão de tijolo em volta do tabuleiro
    pygame.draw.rect(tela, FUNDO, TABULEIRO)
    for y in range(0, ALTURA, TAM_BLOCO):
        desenhar_tijolo(0, y)
        desenhar_tijolo(TABULEIRO.right, y)
    for x in range(TABULEIRO.left, TABULEIRO.right, TAM_BLOCO):
        desenhar_tijolo(x, TABULEIRO.bottom)

    # blocos fixados e a peça caindo (só a parte que já entrou no tabuleiro)
    for (x, y), cor in jogo.travadas.items():
        desenhar_bloco(TABULEIRO.x + x * TAM_BLOCO, TABULEIRO.y + y * TAM_BLOCO, cor)
    for x, y in convert_shape_format(jogo.peca_atual):
        if y >= 0:
            desenhar_bloco(TABULEIRO.x + x * TAM_BLOCO, TABULEIRO.y + y * TAM_BLOCO, jogo.peca_atual.cor)

    # painel do lado direito
    centro = (TABULEIRO.right + 8 + LARGURA) // 2
    desenhar_moldura(pygame.Rect(97, 4, 62, 26), dupla=False)
    escrever("PONTOS", ESCURO, (centro, 12))
    escrever(str(jogo.pontos), ESCURO, (centro, 22))
    desenhar_moldura(pygame.Rect(97, 36, 62, 44), dupla=False)
    escrever("PROXIMA", ESCURO, (centro, 44))
    desenhar_proxima(jogo.proxima_peca, pygame.Rect(97, 50, 62, 28))
    desenhar_moldura(pygame.Rect(97, 86, 62, 26), dupla=False)
    escrever("TEMPO", ESCURO, (centro, 94))
    minutos, segundos = divmod(int(tempo_jogo), 60)
    escrever(f"{minutos}:{segundos:02}", ESCURO, (centro, 104))
    escrever(f"NIVEL {jogo.nivel() + 1}", ESCURO, (centro, 120))
    escrever(jogo.nome, ESCURO, (centro, 134))
    escrever("ESC", ESCURO, (centro, 148))
    escrever("MENU", ESCURO, (centro, 158))

    # quem perdeu mostra PERDEU, o outro VENCEU
    if partida_acabou():
        desenhar_moldura(pygame.Rect(TABULEIRO.x + 4, 56, TABULEIRO.width - 8, 48))
        escrever("PERDEU" if jogo.fim_de_jogo else "VENCEU", ESCURO, (TABULEIRO.centerx, 72))
        if int(tempo * 2) % 2 == 0:
            escrever("TECLA R", MEDIO, (TABULEIRO.centerx, 90))


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

    # menu e ip ficam no meio do quadro; no jogo, cada tabuleiro ocupa uma metade
    quadro.fill(FUNDO)
    if estado == "menu":
        desenhar_menu()
        quadro.blit(tela, (MARGEM_X, 0))
    elif estado == "ip":
        atualizar_ip()
        desenha_ip()
        quadro.blit(tela, (MARGEM_X, 0))
    elif estado == "jogo":
        atualizar_jogo(dt)
        for i, jogo in enumerate(jogos):
            desenhar_jogo(jogo)
            quadro.blit(tela, (i * LARGURA, 0))

    # amplia o quadro pequeno pra janela sem suavizar, por isso fica pixelado
    pygame.transform.scale(quadro, janela.get_size(), janela)
    if EFEITO_LCD:
        janela.blit(efeito_lcd, (0, 0))
    pygame.display.flip()

if conexao is not None:
    conexao.close()
pygame.quit()