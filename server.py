import socket
import json
import uuid
import time
import random
import math
import pygame
import cProfile
import pstats

profiler = cProfile.Profile()
profiler.enable()

SERVER_NAME = "FREEROAM #1"
MAX_PLAYERS = 15
IP = '0.0.0.0'
PORT = 5667
GAMEMODE = "DM/DRIFT/RPG"

ADMINS = ['admin', 'calc0r', 'k1rox']

WORLD_CELLS_X = 300

WORLD_CELLS_Y = 300

TILE_SIZE = 50

game_map = {}

MAX_WARNS = 10

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


def on_quit():
    profiler.disable()

    # Створюємо об’єкт Stats
    stats = pstats.Stats(profiler)

    # Сортуємо по "cumtime" (сукупний час у функції + дочірні виклики)
    stats.sort_stats("cumtime")

    # Друкуємо топ-20 функцій
    stats.print_stats(20)

    stats.dump_stats("server.prof")
    pygame.quit()
    exit()

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



def line_circle_intersection(px, py, dx, dy, cx, cy, r):
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
    # alr on this one i'll have to give the credit to chatgpt
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
            for e in entities.values(): # crazy shit, a for loop in a while loop for a single shot. 
                # should be something more like get_entities_at(gx, gy)
                # will fix it once the performance becomes an issue
                if e is shooter:
                    continue
                t = line_circle_intersection(x0, y0, dx, dy, e['x'], e['y'], e['size']) # some fkin magic going on here
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

def take_damage(victim, damage):
    armour = victim['armour']
    remaining_armour = armour - damage
    if remaining_armour > 0:
        victim['armour'] = remaining_armour
    else:
        victim['armour'] = 0
        # some magic going down there but its logical once you understand it
        victim['hp'] += remaining_armour

    if victim['hp'] <= 0:
        disconnect(get_uuid_from_nickname(victim['nickname']), "You have died")
        return

    send_update_to_all({"type": "hp_change", 'nickname': victim['nickname'], 'new_hp': victim['hp'], 'new_armour': victim['armour']})

def hit(shooter, victim, damage):
    # doing it like that so we can later add stats for shooter or smth
    take_damage(victim, damage)

uuid_to_local_entity = {}


get_weapon_type_cooldown = {'punch': 2}


weapons = {
    'punch': {'type': 'punch', 'damage': 20, 'magazines': 1, 'magazine_size': 99999, 'time_between_shots': 0.5, 'recoil': 0, 'reload_time': 0},
    'pistol': {'type': 'pistol', 'damage': 30, 'magazines': 4, 'magazine_size': 12, 'time_between_shots': 0.2, 'recoil': 2, 'reload_time': 1.3},
    'rifle': {'type': 'rifle', 'damage': 30, 'magazines': 4, 'magazine_size': 30, 'time_between_shots': 0.1, 'recoil': 1.5, 'reload_time': 2},
}

def update_weapons(uuid):
    send_update(uuid, {'type': 'new_weapons', 'new_weapons': uuid_to_entity[uuid]['_weapons']})

def give_weapon(uuid: str, weapon_type: str, magazines=0):
    entity = uuid_to_entity[uuid]
    weapon = weapons[weapon_type].copy()

    if magazines: # custom amount
        weapon['magazines'] = magazines

    if not entity['_weapons'][weapon_type]:
        entity['_weapons'][weapon_type] = weapon
    else:
        entity['_weapons'][weapon_type]['magazines'] += magazines

    entity['_weapons'][weapon_type]['cur_magazine_ammo'] = weapon['magazine_size']

    update_weapons(uuid)
    


def check_circle_point_collision(circle_x, circle_y, radius, point_x, point_y):
    dx = circle_x - point_x
    dy = circle_y - point_y
    return dx*dx + dy*dy <= radius * radius

def play_sound(soundname: str, pos = None):
    update = {"type": "play_sound", "soundname": soundname, "pos": pos}
    send_update_to_all(update)

def get_cur_weapon(entity: dict):
    return entity['_weapons'][entity['selected_weapon_type']]


def shoot(request: dict):
    uuid = request['id']
    entity = uuid_to_entity[request['id']]
    if entity['_can_shoot_at_time'] > now: # ще не спала затримка
        #send_message(uuid, 'you cant shoot yet')
        #print(f"{entity['_can_shoot_at_time']=}")
        return

    weapon_type = entity['selected_weapon_type']
    ammo = entity['_weapons'][weapon_type]['cur_magazine_ammo']
    time_between_shots = weapons[weapon_type]['time_between_shots']

    weapons_type_stats = weapons[weapon_type]

    if ammo < 0:
        #send_message(uuid, 'no ammo')
        return

    ammo -= 1
    entity['_can_shoot_at_time'] = now + time_between_shots
    play_sound(weapon_type+"_shoot_sound", [entity['x'], entity['y']])

    x = entity['x']
    y = entity['y']
    rotation = entity['rotation']

    dx, dy = circularize(rotation, 40)
    endx = x+dx
    endy = y+dy
    if weapon_type == 'punch':
        new_line({"x": x, "y": y,
                "end_x": endx,
                "end_y": endy,
                "time_left": 0.5})
        for other in entities.values():
            if check_circle_point_collision(other['x'], other['y'], other['size'], endx, endy):
                take_damage(other, weapons[weapon_type]['damage'])
                play_sound(weapon_type+"_shot_sound", pos=[other['x'], other['y']])
                return
    else:
        recoil = weapons_type_stats['recoil']
        rotation += random.uniform(recoil, -recoil)
        result = raycast((x, y), rotation, shooter=entity)
        if result:
            target, distance = result
            if target.get('nickname'): # that way we guarantee its an entity cause blocks dont gave a nickname key
                take_damage(target, weapons_type_stats['damage'])
                send_update(uuid, {'type': 'kill_effect'})
            a = circularize(rotation, distance)
            new_line({
                "x": x, "y": y,
                "end_x": x + a[0],
                "end_y": y + a[1],
                "time_left": 0.5
            })
        else:
            end = circularize(rotation, 2000)
            new_line({
                "x": x, "y": y,
                "end_x": x + end[0],
                "end_y": y + end[1],
                "time_left": 0.5
            })
    
    send_message(uuid, 'shot succesfully!')
    return {"shot": True} # хай самі собі пулі рахують, навіть не буду тратити на це час


def handle_reload(request: dict):
    entity = uuid_to_entity[request['id']]
    weapon = get_cur_weapon(entity)
    weapon['magazines'] -= 1
    weapon['cur_magazine_ammo'] = weapons[entity['selected_weapon_type']]['magazine_size'] # ставимо повний для цього типу зброї

    entity['_can_shoot_at_time'] = weapons[entity['selected_weapon_type']]['reload_time']
    play_sound(entity['selected_weapon_type']+"_reload_sound", pos=[entity['x'],entity['y']])
    update_weapons(request['id'])
    


def send_update(_uuid, update):
    to_send_upd[_uuid].append(update)

def send_update_to_all(update: dict):
    for _uuid in uuid_to_entity.keys():
        send_update(_uuid, update)

def hypot(dx, dy) -> float | int:
    a = dx**2
    b = dy**2
    return math.sqrt(a + b)

def warn(uuid, alert_msg=""):
    if alert_msg:
        alert(uuid, alert_msg)
    entity = uuid_to_entity[uuid]
    entity['_warns'] += 1
    if entity['_warns'] > MAX_WARNS:
        disconnect(uuid, alert_msg)

MAX_ALOWED_MOVES_PER_SECONDS = 60

MINIMAL_DIFFRENCE_BETWEEN_MOVES = round(1/(MAX_ALOWED_MOVES_PER_SECONDS+1), 4) # +1 just to be sure that we arent kicking anybody for no reason

print(MINIMAL_DIFFRENCE_BETWEEN_MOVES)

def is_valid_move(entity, rel_move: list) -> bool:

    print(f"{now=}, {entity['_last_moved_at']=}")
    if entity['_last_moved_at'] + MINIMAL_DIFFRENCE_BETWEEN_MOVES > now:
        uuid = get_uuid_from_nickname(entity['nickname'])
        warn(uuid, "You are moving too fast! limit your fps to 60 or you will be kicked!")
        return

    if abs(rel_move[0]) > 4 or abs(rel_move[1]) > 4:
        warn(uuid, "You are moving too fast! stop trying to speedhack or you will be kicked/banned!")
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
    
    entity['_last_moved_at'] = now
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

def send_message(uuid, text, colour=[255, 255, 255]):
    send_update(uuid, {"type": "new_chat_message",'text': text, 'colour': colour})

def send_message_to_all(text, colour=[255, 255, 255]):
    send_update_to_all({"type": "new_chat_message",'text': text, 'colour': colour})

def tp(nickname, x, y):
    entity = entities[nickname]
    entity['x'] = x
    entity['y'] = y
    send_update_to_all({"type": "entity_move", "nickname": entity['nickname'], "new_pos": [entity['x'], entity['y']]})

def explosion(x, y):
    send_update_to_all({"type": "explosion", "coords": [x, y]})

sent_game_to: set[str] = set() # {"uuid", "uuid" ...}

def get_entity_wrapper(entity: dict):
    return {k: v for k, v in entity.items() if not k.startswith("_")}
    # оце я хакер


def get_game_wrapper() -> dict:
    game = {'entities': {}}

    for nickname, entity in entities.items():
        game['entities'][nickname] = get_entity_wrapper(entity)

    return game

def select_weapon(uuid, weapon_type: str):
    entity = uuid_to_entity[uuid]
    entity['selected_weapon_type'] = weapon_type

    send_update_to_all({'type': 'selected_new_weapon', 'nickname': entity['nickname'], 'new_selected_weapon_type': weapon_type})


def disconnect(uuid, reason=""):
    send_update(uuid, {"type": "error", "details": reason or "You have been disconnected!"})

    nickname = uuid_to_entity[uuid]['nickname']
    if nickname in entities:
        entities.pop(nickname)
    send_update_to_all({"type": "player_left", "nickname": nickname})

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
    
    # _ means other players wont see it
    # for example other people shouldnt know that a player has a gun unless he shows it 
    # nor they should see server side things like last_asked_for_update
    entity = {
        "x": 500+random.randint(-200, 200),
        "y": 500+random.randint(-200, 200),
        "colour": colour,
        "nickname": nickname,
        "size": size,
        '_last_asked_for_update': now,
        'rotation': 0,
        'hp': 100,
        'armour': 0, # за замовчуванням не треба
        'selected_weapon_type': 'punch', # і просто потім з цим звертаємось до _weapons щоб типу напряму редагувати
        '_can_shoot_at_time': now,
        '_last_moved_at': now,
        '_warns': 0,
    }

    entities[nickname] = entity
    uuid_to_entity[connection_id] = entity
    to_send_upd[connection_id] = []
    send_update_to_all({"type": "new_join", "nickname": nickname, "entity": get_entity_wrapper(entity)})
    to_send_upd[connection_id] = [] # щоб самому про себе не казало що він зайшов в гру

    entity['_weapons'] = { # default weapons
        'punch': None,
        'pistol': None,
        'rifle': None,
        'RPG': None,
        'submachine': None,
        'shotgun': None,
        }

    give_weapon(connection_id, 'punch') # щоб він сам хоть знав що за punch у нього
    give_weapon(connection_id, 'pistol')
    give_weapon(connection_id, 'rifle')
    select_weapon(connection_id, 'punch')

    return {"id": connection_id}

def handle_get_game(request: dict):
    # щоб сервер не заспамили купою досить дорогих гет гейм
    entity = uuid_to_entity[request['id']]
    if request['id'] not in sent_game_to:
        sent_game_to.add(request['id'])
        return get_game_wrapper()

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
    
    uuid_to_entity[request['id']]['_last_asked_for_update'] = now
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
    #match request['text'].split(" ")[0]:
    #    case "/me":
    #        handle_say(request, colour=[])
    if not is_admin(request['id']):
        return
    match request['text'].split(" ")[0]:

        case "/kick":
            who = request['text'].split(" ")[1]
            nickname = who # doing it like that so that random people cant say xyz left to server and we will accept it
            reason = " ".join(request['text'].split(" ")[2:]) # щоб ігнорувати все до другого пробілу

            uuid = get_uuid_from_nickname(nickname)
            disconnect(uuid, reason or "You have been kicked!")
    
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

        case "/giveweapon":
            nickname = request['text'].split(" ")[1]
            weapon_type = " ".join(request['text'].split(" ")[2:]) # щоб ігнорувати все до другого пробілу
            uuid = get_uuid_from_nickname(nickname)

            print(f"giving {weapon_type=} to {uuid=}")
            give_weapon(uuid, weapon_type)


def handle_say(request: dict):
    if request['text'].startswith("/"):
        return handle_command(request)
    entity = uuid_to_entity[request['id']]
    nickname = entity['nickname']
    text = request['text']
    if len(text) > 50:
        text = text[:50]
    send_update_to_all({"type": "new_chat_message", 'text': f"{nickname}: {text}", "colour": [255, 255, 255]})

def handle_shoot(request: dict):
    return shoot(request)

def handle_select_weapon(request: dict):
    select_weapon(request['id'], request['new_weapon_type'])


req_type_to_func = {
    'join': handle_join,
    'get_game': handle_get_game,
    'get_updates': handle_get_updates,
    'move': handle_move,
    'set_rotation': handle_set_rotation,
    'say': handle_say,
    'shoot': handle_shoot,
    'select_weapon': handle_select_weapon,
    'reload': handle_reload,

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

def main():
    global last_checked_for_inactive, now
    now = time.time()

    request, addr = server.recvfrom(65535)
    request = json.loads(request)

    print(f"GOT REQUEST FROM {addr}, CONTENT: {request}\n")

    #try:
    response = handle_request(request)
    #except Exception as e:
    #    response = {"Error": str(e)}

    if response:
        server.sendto(json.dumps(response).encode(), addr)

    
    if now - last_checked_for_inactive > 5: # кожні 5 секунд
        last_checked_for_inactive = now
        entities = game['entities']
        for nickname, entity in entities.copy().items():
            if entity['_last_asked_for_update'] - now > 2: # довше 2 секунд немає запросів - кік
                entities.pop(nickname)
                send_update_to_all({"type": "player_left", "nickname": nickname})
        game['entities'] = entities

while True:
    try:
        main()
    except KeyboardInterrupt:
        on_quit()