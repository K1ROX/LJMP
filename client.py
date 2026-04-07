import socket
import json
import pygame
import random
import sys
import math
import pyperclip
import time
from pathlib import Path
from typing import Callable
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

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
    if not request.get("id") and not request['type'] == "join":
        request['id'] = ID
    print(f"SENDING: {request}")
    client.sendto(json.dumps(request).encode(), (IP, PORT))
    answer = json.loads(client.recvfrom(65535)[0].decode())
    print(f"ANSWER: {answer}\n")
    if answer.get('Error'):
        raise MultiplayerError(f"Got error message from server: {str(answer.get('Error'))}")
    return answer

ID = send_request({"type": "join", 'nickname': NICKNAME, 'colour': COLOUR})['id']


def on_quit():
    profiler.disable()

    # Створюємо об’єкт Stats
    stats = pstats.Stats(profiler)

    # Сортуємо по "cumtime" (сукупний час у функції + дочірні виклики)
    stats.sort_stats("cumtime")

    # Друкуємо топ-20 функцій
    stats.print_stats(20)

    stats.dump_stats("client.prof")
    send_request({'id': ID, 'type': 'quit'})
    pygame.quit()
    exit()

GAME = send_request({"id": ID, "type": "get_game"})

ENTITIES = GAME['entities']

entities = ENTITIES

Player = ENTITIES[NICKNAME]

BIG_FONT = pygame.font.SysFont("impact", 30)

ASSETS_PATH = current_directory / "assets"

SOUNDS_PATH = ASSETS_PATH / "sounds"

SOUNDS = {filename.stem: pygame.mixer.Sound(str(SOUNDS_PATH / filename)) for filename in SOUNDS_PATH.iterdir()}

# ".".join(str(filename).split(".")[:-1]) ^^^  без розширення файла або краще filename.stem

IMAGES_PATH = ASSETS_PATH / "images"

IMAGES = {filename.stem: pygame.image.load(str(IMAGES_PATH / filename)).convert_alpha() for filename in IMAGES_PATH.iterdir()}


current_music = None

WEAPON_SWITCH_MENU_SONG = ASSETS_PATH / "soundtracks" / "Weapon_switch_sound.mp3"

pos_when_started_selecting_weapons = (0, 0)

def play_music(music):
    global current_music
    current_music = music
    pygame.mixer.music.load(music)
    pygame.mixer.music.play(-1)

def try_play(soundname):
    if SOUNDS.get(soundname):
        SOUNDS.get(soundname).play()
        return True
    
    chat_messages.append((f"failed to load sound {soundname}", (255, 0, 0)))
    return False

nonetexture = pygame.Surface((100, 100))
nonetexture.fill((0,0,0))
col = (255, 0, 220)
pygame.draw.rect(nonetexture, col, (50, 0, 50, 50))
pygame.draw.rect(nonetexture, col, (0, 50, 50, 50))

def try_load_img(imgname):
    if IMAGES.get(imgname):
        return IMAGES.get(imgname)
    
    chat_messages.append(f"failed to load image {imgname}", (255, 0, 0))
    return False

alert_surf = pygame.Surface((1920, 1080), pygame.SRCALPHA)
alert_time = 0
alert_started_at = 0
alert_text = "" 

alert_sound = pygame.mixer.Sound(current_directory / "alert.mp3")

lines = []

todo = []

now = time.time()

def do(task: Callable, after: int=1, sender=None):
    todo.append({"task": task, "time": now + after, "sender": sender})

def after(time: int, task: Callable, sender=None):
    do(task, time, sender)

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


def kill_effect():
    # cool kill effect like in gta 5
    overlay_colour((100, 100, 150, 100), 0.2)

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
    chat_messages.append((f"{update['text']}", update['colour']))

    chat_surf.fill((0,0,0,0))
    if len(chat_messages) > 20:
        chat_messages[:] = chat_messages[-20:]
        # Тоді об'єкт списку не змінюється, лише його вміст.
    for i, obj in enumerate(chat_messages[::-1]):
        text, col = obj
        surf = FONT.render(text, 1, col)
        chat_surf.blit(surf, (7, 360-i*20))

def handle_error(update: dict):
    raise MultiplayerError(update['details'])

def handle_alert(update: dict):
    alert(update['text'])

def handle_hp_change(update: dict):
    nickname = update['nickname']
    entity = ENTITIES[nickname]
    entity['armour'] = update['new_armour']
    entity['hp'] = update['new_hp']

def handle_new_line(update: dict):
    print('got new line update!!')
    lines.append(update['line'])
    print(lines)

def handle_explosion(update: dict):
    Explosion(*update['coords'])

def handle_new_weapons(update: dict):
    Player['_weapons'] = update['new_weapons']

def handle_selected_new_weapon(update: dict):
    entity = ENTITIES[update['nickname']]
    entity['selected_weapon_type'] = update['new_selected_weapon_type']

def handle_play_sound(update: dict):
    soundname = update['soundname']
    try_play(soundname)

def handle_kill_effect(update: dict):
    kill_effect()

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
    'new_weapons': handle_new_weapons,
    'selected_new_weapon': handle_selected_new_weapon,
    'play_sound': handle_play_sound,
    'kill_effect': handle_kill_effect,

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

screen_overlay = pygame.Surface((1920, 1080), pygame.SRCALPHA)

overlay_fading_away = False
fading_away_speed = 5

def const_overlay(colour):
    screen_overlay.fill(colour)
    screen_overlay.set_alpha(255)

def overlay_colour(colour, start_fading_away_after=2, speed=5):
    global overlay_fading_away, fading_away_speed
    fading_away_speed = speed
    overlay_fading_away = False
    screen_overlay.fill(colour)
    screen_overlay.set_alpha(255)
    do(stop_fading_away, start_fading_away_after)

def stop_fading_away():
    global overlay_fading_away
    overlay_fading_away = True


def get_index_of_selected_weapon() -> int:
    dx = mx-x_center
    dy = my-y_center
    degrees_from_center = get_degrees(dx, dy)
    step = 360 / 8
    degrees_from_center += 180
    selected = int(degrees_from_center/step+(360/8)/2)
    selected += 2
    #while selected > 8:
    #    selected -= 8
    selected = selected % 8
    return selected

def stop_overlay():
    screen_overlay.fill((0, 0, 0, 0))

def stop_music():
    global current_music
    current_music = None
    pygame.mixer.music.stop()


weapon_switch_surf = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

offsetx = -try_load_img('punch').get_rect().width//2
offsety = -try_load_img('punch').get_rect().height//2


weapons_surf_circle = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)

circle_offset = 300


def upd_weapon_circle():
    weapons_surf_circle.fill((0,0,0,0))
    pygame.draw.circle(weapons_surf_circle, (0, 0, 0), (x_center, y_center), 360, 150)
    pygame.draw.circle(weapons_surf_circle, (50, 50, 50), (x_center, y_center), 350, 130)
    weapons_surf_circle.set_alpha(120)
    
upd_weapon_circle()


def upd_weapon_switch_circle():
    upd_weapon_circle()  # оновлюємо, бо x_center/y_center можуть змінюватися
    weapon_switch_surf.fill((0, 0, 0, 0))

    # Позиції та оффсети для кожної зброї
    positions = {
        'punch':      (x_center + offsetx - 50, y_center + offsety + circle_offset - 20),
        'pistol':     (x_center + offsetx - 50, y_center + offsety - circle_offset),
        'rifle':      (x_center + offsetx + circle_offset, y_center + offsety),
        'RPG':        (x_center + offsetx - circle_offset, y_center + offsety),
        'submachine': (x_center + offsetx + circle_offset*0.7 - 20, y_center + offsety - circle_offset*0.7),
        'shotgun':    (x_center + offsetx - circle_offset*0.7, y_center + offsety + circle_offset*0.7),
    }

    # Додаткові зміщення для тексту боєприпасів
    ammo_offsets = {
        'punch':      (0, 0),  # немає боєприпасів
        'pistol':     (150, 100),
        'rifle':      (100, 100),
        'RPG':        (140, 100),
        'submachine': (150, 100),
        'shotgun':    (150, 100),
    }

    for weapon_name, pos in positions.items():
        weapon_data = Player['_weapons'].get(weapon_name)
        if weapon_data:
            # Малюємо картинку
            print(f"loading {weapon_name=}")
            print(f"{try_load_img(weapon_name)=}")
            weapon_switch_surf.blit(try_load_img(weapon_name), pos)

            # Якщо є боєприпаси (не для кулака)
            if weapon_name != 'punch':
                total_ammo = (weapon_data['magazines'] - 1) * weapon_data['magazine_size'] + weapon_data['cur_magazine_ammo']
                ammo_text = FONT.render(f"{total_ammo}", 1, (255, 255, 255))
                ammo_pos = (pos[0] + ammo_offsets[weapon_name][0], pos[1] + ammo_offsets[weapon_name][1])
                weapon_switch_surf.blit(ammo_text, ammo_text.get_rect(center=ammo_pos))


"""if Player.c4_placer:
    weapon_switch_surf.blit(c4_placer_img, (x_center+offsetx-circle_offset*0.7-30, y_center+offsety-circle_offset*0.7+10))
    ammo = FONT.render(f"{(Player.c4_placer.magazines-1)*Player.c4_placer.magazine_size+Player.c4_placer.ammo}", 1, (255 ,255, 255))
    weapon_switch_surf.blit(ammo, ammo.get_rect(center=((x_center+offsetx-circle_offset*0.7-30+150, y_center+offsety-circle_offset*0.7+10+100))))
if Player.c4_detonator:
    weapon_switch_surf.blit(c4_detonator_img, (x_center+offsetx+circle_offset*0.7-60, y_center+offsety+circle_offset*0.7))"""

#weapon_switch_surf.blit(shotgun_img, (x_center+offsetx+circle_offset*0.7-60, y_center+offsety+circle_offset*0.7))

while_opacent_circle = pygame.Surface((100, 100), pygame.SRCALPHA) # white blyat but doesnt matter

pygame.draw.circle(while_opacent_circle, (255, 255, 255), (50, 50), 50)

while_opacent_circle.set_alpha(120)
weapons_surf_circle.set_alpha(120)

Weapon_switch_menu_open = False



def update_game_state():
    global entities, cam, mx, my, chatOpen, chat, text_cursor_pos, Weapon_switch_menu_open
    updates = send_request({"id": ID, "type": "get_updates"})['updates']


    if updates != 0:
        for update in updates:
            handle_update(update)


    entities = GAME['entities']

    cam = [-Player['x']+x_center, -Player['y']+y_center]

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
            elif event.key == pygame.K_r:
                send_request({"type": "reload"})
            elif event.key == pygame.K_TAB:
                global pos_when_started_selecting_weapons
                play_music(WEAPON_SWITCH_MENU_SONG)
                pos_when_started_selecting_weapons = mx, my
                upd_weapon_switch_circle() # in case player got a new weapon or lost an old one
                Weapon_switch_menu_open = True
                pygame.mouse.set_pos(x_center, y_center)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            ...
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_TAB:
                #screen_overlay()
                stop_overlay()
                stop_music()
                weapon_index = get_index_of_selected_weapon()
                alert(f"{weapon_index=}")
                match weapon_index:
                    case 1:
                        pass
                    case 2:
                        print("wanted to select pistol")
                        if Player['_weapons']['pistol']:
                            print("there is what we wanted, sending req")
                            send_request({'type': 'select_weapon', 'new_weapon_type': 'pistol'})
                    case 3:
                        if Player['_weapons']['submachine']:
                            send_request({'type': 'select_weapon', 'new_weapon_type': 'submachine'})
                    case 4:
                        if Player['_weapons']['rifle']:
                            send_request({'type': 'select_weapon', 'new_weapon_type': 'rifle'})
                    case 5:
                        pass
                    case 6:
                        if Player['_weapons']['punch']:
                            send_request({'type': 'select_weapon', 'new_weapon_type': 'punch'})
                    case 7:
                        if Player['_weapons']['shotgun']:
                            send_request({'type': 'select_weapon', 'new_weapon_type': 'shotgun'})
                    case 0:
                        if Player['_weapons']['RPG']:
                            send_request({'type': 'select_weapon', 'new_weapon_type': 'RPG'})
                Weapon_switch_menu_open = False    
                #mx = pos_when_started_selecting_weapons[0] - (x_center-mx) # so like the mouse "actually" moved while we were selecting
                #my = pos_when_started_selecting_weapons[1] - (y_center-my)
                # actually we dont need it
                pygame.mouse.set_pos(pos_when_started_selecting_weapons)


    move_x, move_y = 0, 0
    keys = pygame.key.get_pressed()

    speed = 2 # if you change it to higher than 2 server simply wont let you move

    if keys[pygame.K_w]:
        move_y = -speed
    if keys[pygame.K_s]:
        move_y = speed
    if keys[pygame.K_a]:
        move_x = -speed
    if keys[pygame.K_d]:
        move_x = speed

    if move_x or move_y:
        if keys[pygame.K_LSHIFT]:
            move_x *= 2
            move_y *= 2
        send_request({"id": ID, "type": "move", "rel_move": [move_x, move_y]})


    new_mx, new_my = pygame.mouse.get_pos()
    if new_mx != mx or new_my != my:
        send_request({"id": ID, "type": "set_rotation", "rotation": get_degrees(x_center-mx, y_center-my)-180})

    mx = new_mx
    my = new_my


    left, middle, right =  pygame.mouse.get_pressed()
    if left:
        print(Player)
        if Player['_weapons'][Player['selected_weapon_type']]['cur_magazine_ammo'] <= 0:
            try_play('empty_ammo')
            send_request({"type": "reload"})
        else:
            answer = send_request({'id': ID, 'type': "shoot"})
            if answer.get("shot") == True:
                Player['_weapons'][Player['selected_weapon_type']]['cur_magazine_ammo'] -= 1

def camerize(x, y):
    return (x+cam[0], y+cam[1])



chat_messages: list[tuple[str, tuple[int,int,int]]] = [] # [(text, [r,g,b,]), (text, [r,g,b,]), ...]

pygame.mouse.set_visible(False)

now = time.time()

particles = set()

def draw_entity(entity: dict):
    x, y = camerize(entity['x'], entity['y'])

    lx, ly = circularize(entity['rotation'], 30)

    #temp = pygame.Surface((60, 60), pygame.SRCALPHA)
    #pygame.draw.line(temp, (0, 255, 0, 128), (30, 30), (30+lx, 30+ly), 5)
    #screen.blit(temp, (x-30, y-30))

    pygame.draw.circle(screen, entity['colour'], (x, y), entity['size'])
    # hands, weapon
    rotation = entity['rotation']
    match entity['selected_weapon_type']:
        case 'punch': # just hands
            right_arm_placement = circularize(rotation+70, 15) # or it may be left idk
            left_arm_placement = circularize(rotation-70, 15)

            pygame.draw.circle(screen, (250, 250, 250), (x+right_arm_placement[0], y+right_arm_placement[1]), 5)
            pygame.draw.circle(screen, (250, 250, 250), (x+left_arm_placement[0], y+left_arm_placement[1]), 5) # lets try them being white

        case 'pistol': # holding a pistol
            right_arm_placement = circularize(rotation+10, 20) # or it may be left idk
            left_arm_placement = circularize(rotation-10, 20)

            pygame.draw.circle(screen, (250, 250, 250), (x+right_arm_placement[0], y+right_arm_placement[1]), 5)
            pygame.draw.circle(screen, (250, 250, 250), (x+left_arm_placement[0], y+left_arm_placement[1]), 5) # lets try them being white

            # and the weapon itself
            circ = circularize(rotation, 15)
            start = x+circ[0], y+circ[1]

            circ = circularize(rotation, 13)
            shadow_start = x+circ[0], y+circ[1]

            circ = circularize(rotation, 35)
            end = x+circ[0], y+circ[1]

            circ = circularize(rotation, 37)
            shadow_end = x+circ[0], y+circ[1]

            pygame.draw.line(screen, (0,0,0), shadow_start, shadow_end, 10) # with the shadow ofc
            pygame.draw.line(screen, (50, 50, 50), start, end, 6)
        case 'rifle': # holding a long rifle
            right_arm_placement = circularize(rotation+10, 20) # or it may be left idk
            left_arm_placement = circularize(rotation-5, 40)

            pygame.draw.circle(screen, (250, 250, 250), (x+right_arm_placement[0], y+right_arm_placement[1]), 5)
            pygame.draw.circle(screen, (250, 250, 250), (x+left_arm_placement[0], y+left_arm_placement[1]), 5) # lets try them being white

            # and the weapon itself
            circ = circularize(rotation, 15)
            start = x+circ[0], y+circ[1]

            circ = circularize(rotation, 13)
            shadow_start = x+circ[0], y+circ[1]

            circ = circularize(rotation, 45)
            end = x+circ[0], y+circ[1]

            circ = circularize(rotation, 47)
            shadow_end = x+circ[0], y+circ[1]

            pygame.draw.line(screen, (0,0,0), shadow_start, shadow_end, 10) # with the shadow ofc
            pygame.draw.line(screen, (50, 50, 50), start, end, 6)

    if entity is Player:
        return # cause we dont need our hp nor our nickname

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
    opacity_50.fill((0, 0, 0, 0))
    print(lines)
    for line in lines[:]:
        line["time_left"] -= dt
        if line["time_left"] <= 0:
            lines.remove(line)
            continue
        alpha = 255
        if line["time_left"] < 0.2:
            alpha = int(255 * (line["time_left"] / 0.2))
        print(f'drawing at, {line["x"] + cam[0]=}, {line["y"] + cam[1]=}, {line["end_x"] + cam[0], line["end_y"] + cam[1]=}')
        pygame.draw.line(opacity_50, (200, 200, 0, alpha), (line["x"] + cam[0], line["y"] + cam[1]), (line["end_x"] + cam[0], line["end_y"] + cam[1]), 3)
    screen.blit(opacity_50, (0, 0))


def render_entities():
    for entity in entities.values():
        draw_entity(entity)

def render_particles():
    if particles:
        for particle in particles.copy():
            particle.draw()
    screen.blit(particles_surf)
    particles_surf.fill((0, 0, 0, 0))


minimap_surf = pygame.Surface((300, 300), pygame.SRCALPHA)
minimap_surf.fill((0, 0, 0))

map_y_center = 300//2+HEIGHT-310
map_x_center = 300//2+10


def render_minimap():
    screen.blit(minimap_surf, (10, HEIGHT-320), (-cam[0]*0.04+35+5-150, -cam[1]*0.04+20-10-150, 300, 300))

def highlight_selected_weapon():
    selected = get_index_of_selected_weapon()
    selected *= 360/8
    dx, dy = circularize(selected, 285)
    dx = -dx
    dy = -dy
    screen.blit(while_opacent_circle, (x_center+dx-50, y_center+dy-50))

chat_surf = pygame.Surface((600, 380), pygame.SRCALPHA)
chat_surf.fill((0, 0, 0, 0))


def render_UI():
    global text_cursor_time

    if not Weapon_switch_menu_open:
        crosshair_colour = (255, 255, 255)
        pygame.draw.circle(screen, (0, 0, 0), (mx, my), 5+3)
        pygame.draw.circle(screen, (crosshair_colour), (mx, my), 5)


    # Chat input
    pygame.draw.rect(screen, (50, 50, 50), (5, HEIGHT-320-5, 310, 330))

    pygame.draw.rect(screen, (0, 125, 73), (10-2, HEIGHT-16, 150, 7))
    pygame.draw.rect(screen, (16, 199, 123), (10-2, HEIGHT-16, Player['hp']*1.5, 7))

    pygame.draw.rect(screen, (17, 77, 117), (10+150+2, HEIGHT-16, 150, 7))
    if Player['armour']:
        pygame.draw.rect(screen, (20, 125, 188), (10+150+2, HEIGHT-16, Player['armour']*1.5, 7))

    render_minimap()

    screen.blit(chat_surf, (7, 0))
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

    angle = Player['rotation']
    a = circularize(angle, 10)
    b = circularize(angle-120, 5)
    c = circularize(angle+120, 5)

    point_a = map_x_center+a[0], map_y_center+a[1]
    point_b = map_x_center+b[0], map_y_center+b[1]
    point_c = map_x_center+c[0], map_y_center+c[1]


    pygame.draw.polygon(screen, (100, 200, 100), (point_a, point_b, point_c), 0)

    if Weapon_switch_menu_open:
        screen.blit(weapons_surf_circle)
        highlight_selected_weapon()
        screen.blit(weapon_switch_surf)
        const_overlay((50, 100, 50, 100))



def render():
    screen.fill((20, 20, 20))

    render_blocks_nearby()
    render_lines()
    render_entities()
    render_UI()

    if not screen_overlay.get_alpha() < 10:
        screen.blit(screen_overlay, (0, 0))
        if overlay_fading_away:
            screen_overlay.set_alpha(screen_overlay.get_alpha() - fading_away_speed)

    
    pygame.display.flip()
    Clock.tick(60) # limiting to 60 fps

while True:
    try:
        now = time.time()
        update_game_state()
        render()
        dt = Clock.tick(60) / 1000.0 # 24 fps for testing and not flooding console
    except KeyboardInterrupt:
        on_quit()