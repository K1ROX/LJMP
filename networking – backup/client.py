import socket
import json
import pygame
import random
import sys
import math
import pyperclip
import time
from pathlib import Path
#IP = '127.0.0.1'
#PORT = 9999

class MultiplayerError(Exception):
    pass


if len(sys.argv) == 0:
    raise MultiplayerError("No nickname or IP-adress provided! Usage: client.py <nickname> <adress>")

if len(sys.argv) == 1:
    raise MultiplayerError("You must enter your nickname!")

NICKNAME = sys.argv[1]


if len(sys.argv) == 2:
    raise MultiplayerError("You must enter IP-adress!")

adress = sys.argv[2]
if not ":" in adress or not "." in adress:
    raise MultiplayerError("Invalid IP adress")
IP = adress.split(":")[0]
PORT = int(adress.split(":")[1])


COLOUR = random.choice([[250, 250, 250], [50, 50, 50], [200, 50, 50], [50, 200, 50], [50, 50, 200]])

current_directory = Path(__file__).parent

pygame.init()
WIDTH, HEIGHT = 1600, 900
x_center = WIDTH // 2
y_center = HEIGHT // 2

Clock = pygame.time.Clock()

screen = pygame.display.set_mode((WIDTH, HEIGHT))

FONT = pygame.font.SysFont("consolas", 18)

client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_request(request: dict):
    print(f"SENDING: {request}")
    client.sendto(json.dumps(request).encode(), (IP, PORT))
    answer = json.loads(client.recvfrom(1024)[0].decode())
    print(f"ANSWER: {answer}\n")
    if answer.get('Error'):
        raise MultiplayerError(f"Got error message from server: {str(answer.get('Error'))}")
    return answer

ID = send_request({"type": "join", 'nickname': NICKNAME, 'colour': COLOUR})['id']


def on_quit():
    send_request({'id': ID, 'type': 'quit'})
    pygame.quit()
    exit()

GAME = send_request({"id": ID, "type": "get_game"})

ENTITIES = GAME['entities']

Player = ENTITIES[NICKNAME]

BIG_FONT = pygame.font.SysFont("impact", 30)

alert_surf = pygame.Surface((1920, 1080), pygame.SRCALPHA)
alert_time = 0
alert_started_at = 0
alert_text = "" 

alert_sound = pygame.mixer.Sound(current_directory / "alert.mp3")

lines = []

def alert(text, silent=False, colour=(255, 255, 255), _alert_time=5, add_to_cur_text = False):
    global alert_surf, alert_time, alert_started_at, alert_text
    if not silent:
        alert_sound.play()
    text = str(text)
    if add_to_cur_text:
        alert_text = text if not alert_text else alert_text+"\n\n"+text
    else:
        alert_text = text
    alert_time = _alert_time
    alert_started_at = time.time()
    alert_surf.fill((0, 0, 0, 0))
    
    black_shadow = BIG_FONT.render(alert_text, 1, (50, 50, 50))
    main = BIG_FONT.render(alert_text, 1, colour, (0, 0, 0))
    rect = main.get_rect(topleft=(50, 50))
    pygame.draw.rect(alert_surf, (0, 0, 0), (rect.x-5, rect.y-5, rect.width+10, rect.height+10))
    for x in (-2, 0, 2):
        for y in (-2, 0, 2):
            alert_surf.blit(black_shadow, (rect.x+x, rect.y+y))
    alert_surf.blit(main, rect)


particles = set()

# -------------------- Particles & explosion --------------------
particles_surf = pygame.Surface((1920, 1080), pygame.SRCALPHA)
class Particle:
    def __init__(self, x, y, colour=(255,255,255), size=10, dx=1, dy=1, sizechange=1, opacity=200, opacitychange=-1):
        self.rect = pygame.Rect(x, y, size, size)
        self.opacity = opacity
        self.colour = colour
        self.dx = dx
        self.dy = dy
        self.sizechange = 0.2
        self.opacitychange = opacitychange
        particles.add(self)
    
    def draw(self):
        if abs(self.rect.x - Player.x) > 2000 or abs(self.rect.y - Player.y) > 2000:
            if self in particles:
                particles.remove(self)
            return
        self.rect.x += self.dx
        self.rect.y += self.dy
        self.rect.width += self.sizechange
        self.rect.height += self.sizechange
        self.opacity += self.opacitychange

        try:
            if self.rect.x + cam[0] < -300 or self.rect.x + cam[0] > 2200:
                return
            if self.rect.y + cam[1] < -300 or self.rect.y + cam[1] > 1500:
                return
            pygame.draw.rect(particles_surf, (*self.colour, int(self.opacity)), (self.rect.x + cam[0], self.rect.y + cam[1], self.rect.width, self.rect.height))
        except ValueError:
            if self in particles:
                particles.remove(self)



def Explosion(x, y):
    for i in [0, 1]: # шоб було побільше партіклів
        Particle(x-15, y-15, (242, 245, 66), 50, dx=+random.randint(-2, 2), dy=+random.randint(-2, 2), sizechange=1, opacitychange=-2)
        Particle(x-15, y-15, (242, 245, 66), 50, dx=+random.randint(-2, 2), dy=+random.randint(-2, 2), sizechange=1, opacitychange=-2)
        Particle(x-15, y-15, (242, 245, 66), 50, dx=+random.randint(-2, 2), dy=+random.randint(-2, 2), sizechange=1, opacitychange=-2)

        Particle(x-15+random.randint(-20, 20), y-15+random.randint(-20, 20), (212, 156, 28), 30, dx=random.randint(-2, 2), dy=random.randint(-2, 2), sizechange=0, opacitychange=-1)
        Particle(x-15+random.randint(-20, 20), y-15+random.randint(-20, 20), (212, 156, 28), 30, dx=random.randint(-2, 2), dy=random.randint(-2, 2), sizechange=0, opacitychange=-1)
        Particle(x-15+random.randint(-20, 20), y-15+random.randint(-20, 20), (212, 156, 28), 30, dx=random.randint(-2, 2), dy=random.randint(-2, 2), sizechange=0, opacitychange=-1)
        Particle(x-15+random.randint(-20, 20), y-15+random.randint(-20, 20), (212, 156, 28), 30, dx=random.randint(-2, 2), dy=random.randint(-2, 2), sizechange=0, opacitychange=-1)

        Particle(x-15+random.randint(-20, 20), y-15+random.randint(-20, 20), (219, 89, 37), 20, dx=random.randint(-3, 3), dy=random.randint(-3, 3), sizechange=0, opacitychange=-1)
        Particle(x-15+random.randint(-20, 20), y-15+random.randint(-20, 20), (219, 89, 37), 20, dx=random.randint(-3, 3), dy=random.randint(-3, 3), sizechange=0, opacitychange=-1)
        Particle(x-15+random.randint(-20, 20), y-15+random.randint(-20, 20), (219, 89, 37), 20, dx=random.randint(-3, 3), dy=random.randint(-3, 3), sizechange=0, opacitychange=-1)


def handle_entity_move(update: dict):
    nickname = update['nickname']
    ENTITIES[nickname]['x'] = update['new_pos'][0]
    ENTITIES[nickname]['y'] = update['new_pos'][1]

def handle_new_join(update: dict):
    ENTITIES[update['nickname']] = update['entity']

def handle_player_left(update: dict):
    ENTITIES.pop(update['nickname'])

def handle_rotation_change(update: dict):
    ENTITIES[update['nickname']]['rotation'] = update['rotation']

def handle_new_chat_message(update: dict):
    global chat_messages
    chat_messages.append(f"{update['nickname']}: {update['text']}")

    chat_surf.fill((0,0,0,0))
    if len(chat_messages) > 20:
        chat_messages[:] = chat_messages[-20:]
        # Тоді об'єкт списку не змінюється, лише його вміст.
    for i, text in enumerate(chat_messages[::-1]):
        surf = FONT.render(text, 1, (255, 255, 255))
        chat_surf.blit(surf, (7, 360-i*20))

def handle_error(update: dict):
    raise MultiplayerError(update['details'])

def handle_alert(update: dict):
    alert(update['text'])

def handle_hp_change(update: dict):
    nickname = update['nickname']
    entity = entities[nickname]
    entity['armour'] = update['armour']
    entity['hp'] = update['hp']

def handle_new_line(update: dict):
    lines.append(update['line'])

def handle_explosion(update: dict):
    Explosion(*update['coords'])

upd_type_to_func = {
    "entity_move": handle_entity_move,
    "new_join": handle_new_join,
    "player_left": handle_player_left,
    "rotation_change": handle_rotation_change,
    "new_chat_message": handle_new_chat_message,
    "alert": handle_alert,
    "hp_change": handle_hp_change,
    'new_line': handle_new_line,
    'explosion': handle_explosion,

    "error": handle_error,
}

def handle_update(update):
    func = upd_type_to_func.get(update['type'])
    if not func:
        raise MultiplayerError(f"Unable to handle {update['type']}")
    func(update)




def circularize(degrees, radius):
    radians = math.radians(degrees)
    return math.cos(radians) * radius, math.sin(radians) * radius

mx, my = 0, 0

opacity_50 = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
opacity_50.set_alpha(128)

def get_degrees(dx, dy):
    return math.degrees(math.atan2(dy, dx))

chat = ""
chatOpen = False
text_cursor_pos = 0
text_cursor_time = 0

def update_game_state():
    global entities, cam, mx, my, chatOpen, chat, text_cursor_pos
    updates = send_request({"id": ID, "type": "get_updates"})['updates']


    if updates != 0:
        for update in updates:
            handle_update(update)


    entities = GAME['entities']

    cam = [Player['x']-x_center, Player['y']-y_center]

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            on_quit()
    

        if event.type == pygame.KEYDOWN:

            # ----------------- Chat -----------------
            if event.key == pygame.K_t:
                if not chatOpen:
                    chatOpen = True
                    pygame.mouse.set_visible(chatOpen)
                    continue
            elif event.key == pygame.K_SLASH:
                if not chatOpen:
                    if not chat:
                        chat = "/"
                        text_cursor_pos = 1
                    chatOpen = True
                    pygame.mouse.set_visible(chatOpen)
                    continue
            if event.key == pygame.K_v and (pygame.key.get_mods() & pygame.KMOD_CTRL):
                to_paste = pyperclip.paste()
                first_part = chat[0:text_cursor_pos]
                second_part = chat[text_cursor_pos:]
                chat = first_part + to_paste + second_part
                chat = chat[:50]
                text_cursor_pos += len(to_paste)
                if text_cursor_pos > 50: text_cursor_pos = 50
                continue
            elif event.key == pygame.K_F6:
                chatOpen = not chatOpen
                pygame.mouse.set_visible(chatOpen)
                continue

            elif event.key == pygame.K_LEFT:
                if pygame.key.get_mods() & pygame.KMOD_CTRL & pygame.KMOD_SHIFT:
                    text_cursor_pos = 0
                if pygame.key.get_mods() & pygame.KMOD_CTRL:
                    text_cursor_pos = 0
                    continue
                if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    text_cursor_pos = max(0, text_cursor_pos - 1)
                    continue
                text_cursor_pos = max(0, text_cursor_pos - 1)
                continue

            elif event.key == pygame.K_RIGHT:
                if pygame.key.get_mods() & pygame.KMOD_CTRL & pygame.KMOD_SHIFT:
                    text_cursor_pos = len(chat)
                if pygame.key.get_mods() & pygame.KMOD_CTRL:
                    text_cursor_pos = len(chat)
                    continue
                if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    text_cursor_pos = max(0, text_cursor_pos + 1)
                    continue
                text_cursor_pos = min(len(chat), text_cursor_pos + 1)
                continue


            elif event.key == pygame.K_ESCAPE:
                if chatOpen:
                    chatOpen = False
                    pygame.mouse.set_visible(False)
                #else:
                #    woosh_sound.play()
                #    toggle_pause()
            elif event.key == pygame.K_BACKSPACE and chatOpen:
                if text_cursor_pos == len(chat):
                    text_cursor_pos -= 1
                    if text_cursor_pos < 0:
                        text_cursor_pos = 0
                    chat = chat[:-1]
                    continue
                else:
                    first_part = chat[0:text_cursor_pos-1]
                    second_part = chat[text_cursor_pos:]
                    chat = first_part + second_part
                    if text_cursor_pos < 0:
                        text_cursor_pos = 0
                    text_cursor_pos -= 1
                    continue
            elif event.key == pygame.K_RETURN and chatOpen:
                send_request({'id': ID, 'type': 'say', 'text': chat})
                chat = ""
                chatOpen = False
                text_cursor_pos = 0
                pygame.mouse.set_visible(chatOpen)
            elif chatOpen and len(chat) < 50:
                typed = event.unicode
                if typed:
                    first_part = chat[0:text_cursor_pos]
                    second_part = chat[text_cursor_pos:]
                    first_part += typed
                    chat = first_part + second_part
                    text_cursor_pos += 1
                    continue



    move_x, move_y = 0, 0
    keys = pygame.key.get_pressed()
    if keys[pygame.K_w]:
        move_y = -2
    if keys[pygame.K_s]:
        move_y = 2
    if keys[pygame.K_a]:
        move_x = -2
    if keys[pygame.K_d]:
        move_x = 2

    if move_x or move_y:
        send_request({"id": ID, "type": "move", "rel_move": [move_x, move_y]})


    new_mx, new_my = pygame.mouse.get_pos()
    if new_mx != mx or new_my != my:
        send_request({"id": ID, "type": "set_rotation", "rotation": int(get_degrees(x_center-mx, y_center-my))-180})

    mx = new_mx
    my = new_my

def camerize(x, y):
    return (x-cam[0], y-cam[1])

chat_surf = pygame.Surface((600, 380), pygame.SRCALPHA)
chat_surf.fill((0, 0, 0, 0))

chat_messages = []

pygame.mouse.set_visible(False)

now = time.time()

particles = set()

def draw_entity(entity: dict):
    x, y = camerize(entity['x'], entity['y'])

    lx, ly = circularize(entity['rotation'], 30)

    pygame.draw.line(screen, (0, 255, 0, 128), (x, y), (x + lx, y + ly), 5)

    pygame.draw.circle(screen, entity['colour'], (x, y), entity['size'])
    print("drawing at", x, y)

    nickname = entity['nickname']
    name_surf = FONT.render(nickname, 1, (255, 255, 255))
    rect = name_surf.get_rect(midtop=(x, y-40))
    screen.blit(name_surf, rect)

    pygame.draw.rect(screen, (0,0,0), (x-25, y-20, 44, 7))
    pygame.draw.rect(screen, (255,0,0), (x-25+2, y-20+2, entity['hp']/2.5, 7-4))

    if entity['armour']:
        pygame.draw.rect(screen, (0,0,0), (x-25, y-27, 44, 7))
        pygame.draw.rect(screen, (255,255,255), (x-25+2, y-27+2, entity['armour']/2.5, 7-4))



def render_blocks_nearby():
    return

def render_lines():
    for line in lines[:]:
        line["time_left"] -= dt
        if line["time_left"] <= 0:
            lines.remove(line)
            continue
        alpha = 255
        if line["time_left"] < 0.2:
            alpha = int(255 * (line["time_left"] / 0.2))
        pygame.draw.line(opacity_50, (200, 200, 0, alpha), (line["x"] + cam[0], line["y"] + cam[1]), (line["end_x"] + cam[0], line["end_y"] + cam[1]), 3)
    screen.blit(opacity_50, (0, 0))
    opacity_50.fill((0, 0, 0, 0))


def render_entities():
    for entity in entities.values():
        draw_entity(entity)

def render_particles():
    if particles:
        for particle in particles.copy():
            particle.draw()
    screen.blit(particles_surf)
    particles_surf.fill((0, 0, 0, 0))


def render():
    screen.fill((20, 20, 20))
    render_blocks_nearby()
    render_lines()
    render_entities()

    global text_cursor_time
    screen.fill((20, 20, 20))
    screen.blit(opacity_50)
    opacity_50.fill((0,0,0,0)) # на 1 кадр запізнюється, можна виправити, але мб потім

    crosshair_colour = (255, 255, 255)
    pygame.draw.circle(screen, (0, 0, 0), (mx, my), 5+3)
    pygame.draw.circle(screen, (crosshair_colour), (mx, my), 5)


    if chatOpen:
        pygame.draw.rect(screen, (255, 255, 255), (8, 398, 604, 39))
        pygame.draw.rect(screen, (0, 0, 0), (10, 400, 600, 35))
        text = FONT.render(chat, True, (255, 255, 255))
        screen.blit(text, (15, 405))
    
        if text_cursor_time >= 0 and text_cursor_time < 40:
            offset = FONT.size(chat[:text_cursor_pos])[0] if text_cursor_pos > 0 else 0
            pygame.draw.line(screen, (255, 255, 255), (15 + offset, 405), (15 + offset, 425), 2)
            text_cursor_time += 1
        if text_cursor_time >= 40:
            text_cursor_time += 1
        if text_cursor_time >= 80:
            text_cursor_time = 0

    global alert_time, alert_started_at, alert_text
    if alert_time:
        if now - alert_started_at > alert_time:
            alert_time = 0
            alert_text = ""
        else:
            screen.blit(alert_surf, (0, 0))

    screen.blit(chat_surf, (7, 0))
    pygame.display.flip()
    Clock.tick(60) # limiting to 60 fps

while True:
    now = time.time()
    update_game_state()
    render()
    dt = Clock.tick(60)