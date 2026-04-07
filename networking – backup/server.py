import socket
import json
import uuid
import time
import random
import math
import pygame


SERVER_NAME = "FREEROAM #1"
MAX_PLAYERS = 15
IP = '0.0.0.0'
PORT = 5667
GAMEMODE = "RPG"

ADMINS = ['admin', 'calc0r', 'k1rox']

WORLD_CELLS_X = 300

WORLD_CELLS_Y = 300

TILE_SIZE = 50

game_map = {}

# use udp
server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
server.bind((IP, PORT))

game: dict = {
    "entities": {},
#    "chat": [],
}

entities: dict = game['entities']

uuid_to_entity: dict = {}

to_send_upd: dict = {} # {'uuid': [json, json, json, ...], 'uuid': [json, json, json, ...], ...}


class Block:
    def __setstate__(self, state):
        self.__dict__.update(state)

    def __init__(self, x, y, type=None, colour=(100, 100, 100), collideable=True):
        self.x = x
        self.y = y
        self.colour = colour
        self.rect = pygame.Rect(x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE)
        self.interactable = False
        self.collideable = collideable
        #self.big = big
        if type:
            self.type = type
            match type:
                case "water":
                    self.colour = (52, 107, 235)
                    self.collideable = False
                case "road":
                    self.colour = (40, 40, 40) if colour == (100, 100, 100) else colour # типу щоб наше було вижче дефолтку
                    self.collideable = False
                case "light_road":
                    self.colour = (219,219,215) # типу щоб наше було вижче дефолтку
                    #def on_standing(entity):
                    #    if isinstance(entity, Vehicle):
                    #        entity.speed_modifier = 0.7
                    #self.on_standing = on_standing
                    self.collideable = False
                case "sand":
                    self.colour = (245, 195, 106)
                    self.collideable = False
                case "grass":
                    self.colour = (69, 114, 42)
                    self.collideable = False

                case "door_top":
                    Door(x, y, anchor="top")
                    return
                case "door_bottom":
                    Door(x, y, anchor="bottom")
                    return
                case "door_right":
                    Door(x, y, anchor="right")
                    return
                case "door_left":
                    Door(x, y, anchor="left")
                    return


class Door(Block):
    def __init__(self, x, y, anchor="top", colour=(145, 94, 39)):
        super().__init__(x, y, colour=colour)
        self.interactable = True
        self.open = False
        self.anchor = anchor

        self.base_x = x * TILE_SIZE
        self.base_y = y * TILE_SIZE

        if anchor == "top":
            self.rect = pygame.Rect(self.base_x, self.base_y, TILE_SIZE, 10)
        elif anchor == "bottom":
            self.rect = pygame.Rect(self.base_x, self.base_y + TILE_SIZE - 10, TILE_SIZE, 10)
        elif anchor == "left":
            self.rect = pygame.Rect(self.base_x, self.base_y, 10, TILE_SIZE)
        elif anchor == "right":
            self.rect = pygame.Rect(self.base_x + TILE_SIZE - 10, self.base_y, 10, TILE_SIZE)



def _line_circle_intersection(px, py, dx, dy, cx, cy, r):
    fx = px - cx
    fy = py - cy
    a = dx*dx + dy*dy
    b = 2 * (dx*fx + dy*fy)
    c = fx*fx + fy*fy - r*r
    disc = b*b - 4*a*c
    if disc < 0:
        return None
    disc_s = math.sqrt(disc)
    t1 = (-b - disc_s) / (2*a)
    t2 = (-b + disc_s) / (2*a)
    t = None
    if t1 >= 0:
        t = t1
    elif t2 >= 0:
        t = t2
    return t

def circularize(degrees, radius):
    radians = math.radians(degrees)
    return math.cos(radians) * radius, math.sin(radians) * radius

def get_block(x, y, log=False, return_dict=False):
    if (0 <= x < WORLD_CELLS_X and 0 <= y < WORLD_CELLS_Y):
        block = game_map.get((x, y))

def raycast(start, angle, shooter=None, max_dist=2000):
    cell_size = TILE_SIZE
    dx, dy = circularize(angle, 1)
    x0, y0 = start
    gx = int(x0 // cell_size)
    gy = int(y0 // cell_size)
    step_x = 1 if dx > 0 else -1
    step_y = 1 if dy > 0 else -1
    if dx != 0:
        next_vert = ((gx + (1 if step_x > 0 else 0)) * cell_size - x0) / dx
        delta_dist_x = cell_size / abs(dx)
    else:
        next_vert = float('inf')
        delta_dist_x = float('inf')
    if dy != 0:
        next_hor = ((gy + (1 if step_y > 0 else 0)) * cell_size - y0) / dy
        delta_dist_y = cell_size / abs(dy)
    else:
        next_hor = float('inf')
        delta_dist_y = float('inf')
    dist = 0.0
    while dist < max_dist:
        next_step = min(next_vert, next_hor)
        if 0 <= gx < WORLD_CELLS_X and 0 <= gy < WORLD_CELLS_Y:
            for e in entities(gx, gy)[:]:
                if e is shooter:
                    continue
                t = _line_circle_intersection(x0, y0, dx, dy, e.x, e.y, e.size)
                if t is not None and dist - 1e-6 <= t <= next_step + 1e-6 and t <= max_dist:
                    # e.recoil += 0.7 # типу подавлення: коли у тебе стріляють мінус точність, але я хз мб лишнє
                    return e, t
            cell_block = get_block(gx, gy)
            if cell_block and cell_block.collideable:
                if not (isinstance(cell_block, Door) and cell_block.open):
                    seg_end_x = x0 + dx * next_step
                    seg_end_y = y0 + dy * next_step
                    try:
                        clipped = cell_block.rect.clipline((int(x0), int(y0)), (int(seg_end_x), int(seg_end_y)))
                    except Exception:
                        clipped = ()
                    if clipped:
                        ix, iy = clipped[0]
                        hit_dist = math.hypot(ix - x0, iy - y0)
                        return cell_block, hit_dist
        if next_vert < next_hor:
            dist = next_vert
            next_vert += delta_dist_x
            gx += step_x
        else:
            dist = next_hor
            next_hor += delta_dist_y
            gy += step_y
        if not (0 <= gx < WORLD_CELLS_X and 0 <= gy < WORLD_CELLS_Y):
            return None
    return None


def new_line(line: dict):
    send_update_to_all({"type": 'new_line', 'line': line})

def hit(shooter, victim, damage):
    armour = victim['armour']
    remaining_armour = armour - damage
    if remaining_armour > 0:
        victim['armour'] = remaining_armour
    else:
        victim['armour'] = 0
        # some magic going down there but its logical once you understand it
        victim['hp'] += remaining_armour
    
    send_update_to_all({"type": "hp_change", 'nickname': 'victim', 'new_hp': victim['hp'], 'new_armour': victim['armour']})

class Weapon:
    def shoot(self, shooter, silent=False):
        if self.cooldown > 0:
            return
        if self.ammo <= 0:
            self.cooldown = 0.3
            #if empty_ammo_sound:
            #    empty_ammo_sound.play()
            self.reload()
            return
        if self.shoot_sound and not silent:
            self.shoot_sound.play()
        angle = get_degrees(shooter.looking_towards[0] - shooter.x, shooter.looking_towards[1] - shooter.y)
        angle += random.uniform(-self.recoil - int(self.recoil), self.recoil + int(self.recoil))
        result = raycast((shooter.x, shooter.y), angle, shooter=shooter)
        if result:
            target, distance = result
            #if isinstance(target, Entity):
            #    if isinstance(target, Cop):
            #        shooter.criminality += 200
            #    shooter.criminality += 100
            hit(shooter=shooter, victim=target, damage=self.damage)
            a = circularize(angle, distance)
            new_line({
                "x": shooter.x, "y": shooter.y,
                "end_x": shooter.x + a[0],
                "end_y": shooter.y + a[1],
                "time_left": 0.5
            })
        else:
            end = circularize(angle, 2000)
            new_line({
                "x": shooter.x, "y": shooter.y,
                "end_x": shooter.x + end[0],
                "end_y": shooter.y + end[1],
                "time_left": 0.5
            })
        self.cooldown = self.rate_of_fire
        shooter.recoil += 1.2
        self.ammo -= 1
    def reload(self):
        if self.magazines > 0:
            self.magazines -= 1
            if self.reload_sound:
                self.reload_sound.play()
            self.cooldown = self.reload_time
            self.ammo = self.magazine_size




def send_update(_uuid, update):
    to_send_upd[_uuid].append(update)

def send_update_to_all(update: dict):
    for _uuid in uuid_to_entity.keys():
        send_update(_uuid, update)

def hypot(dx, dy) -> float | int:
    a = dx**2
    b = dy**2
    return math.sqrt(a + b)

def is_valid_move(entity, rel_move: list) -> bool:

    if abs(rel_move[0]) > 2 or abs(rel_move[1]) > 2:
        return False # so that people cant speedhack
    
    new_x = entity['x']+rel_move[0]
    new_y = entity['y']+rel_move[1]

    for other in entities.values(): # obv will change that using prolly chunk system .... or no? anyway for now doing for 10 players at MAX
        if other == entity:
            continue
        if abs(other['x']-new_x) < 25 or abs(other['y']-new_y) < 25: # bounding box
            dx = other['x']-new_x
            dy = other['y']-new_y
            if hypot(dx, dy) < 25:
                return False
            
    return True

def validize_nickname(nickname: str):
    if len(nickname) < 5:
        return "Too short!"
    if len(nickname) > 16:
        return "Too long!"
    if " " in nickname:
        return "Nicknames can't contain spaces!"
    if nickname.lower() == "server": # so that people dont fake them as server messages
        return "Choose a diffrent nickname!"

allowed_colours = [[250, 250, 250], [50, 50, 50], [200, 50, 50], [50, 200, 50], [50, 50, 200]]

def validize_colour(colour: list):
    if colour not in allowed_colours:
        return "Colour not in allowed colours!" # crazy, typing code just like we speak

def get_degrees(dx,dy):
    return math.degrees(math.atan2(dy, dx))

def is_admin(uuid):
    entity = uuid_to_entity[uuid]
    nickname = entity['nickname']
    if nickname in ADMINS:
        return True
    
    return False

def get_uuid_from_nickname(looking_for_nickname):
    for uuid, entity in uuid_to_entity.items():
        if entity['nickname'] == looking_for_nickname:
            return uuid

def alert(uuid, text):
    send_update(uuid, {'type': 'alert', 'text': text})

def chat_alert(uuid, text):
    send_update(uuid, {"type": "new_chat_message", "nickname": "SERVER", 'text': text})

def tp(nickname, x, y):
    entity = entities[nickname]
    entity['x'] = x
    entity['y'] = y
    send_update_to_all({"type": "entity_move", "nickname": entity['nickname'], "new_pos": [entity['x'], entity['y']]})

def explosion(x, y):
    send_update_to_all({"type": "explosion", "coords": [x, y]})

def handle_join(request: dict):
    if len(entities) >= MAX_PLAYERS:
        return {"Error": "Server full!"}
    connection_id = str(uuid.uuid4())
    nickname = request['nickname']
    colour = request['colour']
    size = 15

    why = validize_nickname(nickname)
    if why: return {"Error": f"Invalid nickname! {why}"}

    why = validize_colour(colour)
    if why: return {"Error": f"Invalid colour! {why}"}

    

    if entities.get(nickname, None) is not None:
        return {"Error": "Nickname already in use!"}
    
    entity = {
        "x": 500+random.randint(-200, 200),
        "y": 500+random.randint(-200, 200),
        "colour": colour,
        "nickname": nickname,
        "size": size,
        'last_asked_for_update': now,
        'rotation': 0,
        'hp': 100,
        'armour': 0, # за замовчуванням не треба
        'weapon': None
    }

    entities[nickname] = entity
    uuid_to_entity[connection_id] = entity
    to_send_upd[connection_id] = []
    send_update_to_all({"type": "new_join", "nickname": nickname, "entity": entity})
    to_send_upd[connection_id] = [] # щоб самому про себе не казало що він зайшов в гру
    return {"id": connection_id}

def handle_get_game(request: dict):
    entity = uuid_to_entity[request['id']]
    entity['last_asked_for_update'] = now
    return game

def handle_move(request: dict):
    entity = uuid_to_entity[request['id']]
    rel_move = request['rel_move']

    if is_valid_move(entity, rel_move):
        entity['x'] += rel_move[0]
        entity['y'] += rel_move[1]
        send_update_to_all({"type": "entity_move", "nickname": entity['nickname'], "new_pos": [entity['x'], entity['y']]})
        return
    else:
        return {'Warn': 'Invalid move'}

def handle_get_updates(request: dict):
    updates = to_send_upd[request['id']].copy() # копі щоб при очищуванні не почистити це і не надіслати порожній список

    if updates:
        to_send_upd[request['id']].clear() # очищуємо список бо надіслали оновлення
    return {"type": "updates", "updates": updates}

def handle_get_server_info(request: dict):
    return {
        "Name": SERVER_NAME,
        "Ip": '127.0.0.1'+":"+str(PORT),
        "Players": str(len(entities)),
        "MaxPlayers": str(MAX_PLAYERS),
        "Gamemode": GAMEMODE,
    }

def handle_quit(request: dict):
    entity = uuid_to_entity[request['id']]
    nickname = entity['nickname'] # doing it like that so that random people cant say xyz left to server and we will accept it
    entities.pop(nickname)
    send_update_to_all({"type": "player_left", "nickname": nickname})

def handle_set_rotation(request: dict):
    entity = uuid_to_entity[request['id']]
    entity['rotation'] = request['rotation']
    send_update_to_all({"type": "rotation_change", "nickname": entity['nickname'], 'rotation': request['rotation']})

def handle_command(request: dict):
    if not is_admin(request['id']):
        return
    match request['text'].split(" ")[0]:

        case "/kick":
            who = request['text'].split(" ")[1]
            nickname = who # doing it like that so that random people cant say xyz left to server and we will accept it

            uuid = get_uuid_from_nickname(nickname)
            send_update(uuid, {"type": "error", "details": "You have been kicked!"})
            entities.pop(nickname)
            send_update_to_all({"type": "player_left", "nickname": nickname})
    
        case "/makeadmin":
            nickname = request['text'].split(" ")[1]
            uuid = get_uuid_from_nickname(nickname)
            ADMINS.append(nickname)
            alert(uuid, "You have been promoted to admin!")

        case "/alert":
            nickname = request['text'].split(" ")[1]
            text = " ".join(request['text'].split(" ")[2:]) # щоб ігнорувати все до другого пробілу
            uuid = get_uuid_from_nickname(nickname)
            alert(uuid, text)

        case "/tp":
            nickname = request['text'].split(" ")[1]
            coords = request['text'].split(" ")[2:] # щоб ігнорувати все до другого пробілу
            uuid = get_uuid_from_nickname(nickname)
            tp(uuid, *coords)

        case "/gethere":
            nickname = request['text'].split(" ")[1]
            text = " ".join(request['text'].split(" ")[2:]) # щоб ігнорувати все до другого пробілу
            uuid = get_uuid_from_nickname(nickname)
            to_who_uuid = request['id']
            to_who = uuid_to_entity['to_who_uuid']
            tp(uuid, to_who['x']-50, to_who['y']-50)


def handle_say(request: dict):
    if request['text'].startswith("/"):
        return handle_command(request)
    entity = uuid_to_entity[request['id']]
    nickname = entity['nickname']
    text = request['text']
    if len(text) > 50:
        text = text[:50]
    send_update_to_all({"type": "new_chat_message", "nickname": nickname, 'text': text})

req_type_to_func = {
    'join': handle_join,
    'get_game': handle_get_game,
    'get_updates': handle_get_updates,
    'move': handle_move,
    'set_rotation': handle_set_rotation,
    'say': handle_say,

    'get_server_info': handle_get_server_info,
    'quit': handle_quit,
}

def handle_request(request: dict):
    #locals().update(request) # чисто щоб швидко писати і не уточнювати цей реквест кожного разу

    req_type = request["type"]
    func = req_type_to_func.get(req_type)

    if not func:
        return {"Error": f"Invalid request type: {req_type}"}
    
    answer = func(request)
    if answer:
        return answer
    else:
        return {"ok": True}

last_checked_for_inactive = time.time()

now = time.time()

while True:
    request, addr = server.recvfrom(1024)
    request = json.loads(request)

    print(f"GOT REQUEST FROM {addr}, CONTENT: {request}\n")

    #try:
    response = handle_request(request)
    #except Exception as e:
    #    response = {"Error": str(e)}

    if response:
        server.sendto(json.dumps(response).encode(), addr)

    now = time.time()
    if now - last_checked_for_inactive > 5: # кожні 5 секунд
        last_checked_for_inactive = now
        entities = game['entities']
        for nickname, entity in entities.copy().items():
            if entity['last_asked_for_update'] - now > 2: # довше 2 секунд немає запросів - кік
                entities.pop(nickname)
                send_update_to_all({"type": "player_left", "nickname": nickname})
        game['entities'] = entities