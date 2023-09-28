import yaml
from rich.traceback import install
from rich import print
from itertools import count
import pydantic
import typing
import random
from tabulate import tabulate

install(show_locals=True)


MUTANT = typing.Literal["mutant"]
DOCTOR = typing.Literal["doctor"]
PSYCHOLOGIST = typing.Literal["psychologist"]
GENETICIST = typing.Literal["geneticist"]
TECHNICIAN = typing.Literal["technician"]
HACKER = typing.Literal["hacker"]
SPY = typing.Literal["spy"]
TRAITOR = typing.Literal["traitor"]

hacker_roles = typing.Union[PSYCHOLOGIST, GENETICIST, TECHNICIAN]

class Player(pydantic.BaseModel):
    name: str
    role: typing.Union[MUTANT, DOCTOR, PSYCHOLOGIST, GENETICIST, TECHNICIAN, HACKER, SPY, TRAITOR, None]
    mutant: bool = False
    genome: typing.Literal["Resistant", "Normal", "Weak"] = "Normal"
    dead: bool = False
    paralized: bool = False

    class Spyed(pydantic.BaseModel):
        mutated: bool = False
        paralized: bool = False
        healed: bool = False
        psychologized: bool = False
        geneticized: bool = False

    spyed: Spyed = Spyed()

class Game(pydantic.BaseModel):
    num_weak: int = 1
    num_resistant: int = 1
    players: typing.Dict[str, Player]

def player_who(pred):
    return next(i for i in players.values() if pred(i))

def load():
    loaded = yaml.safe_load(open("players.yaml"))
    loaded['players'] = {k: Player(name=k, role=v) for (k, v) in loaded['players'].items()}
    game = Game(**loaded)
    players = game.players
    players["blank"] = Player(name="blank", role=None)

    return game


game = load()
players = game.players

def modify():
    player_who(lambda i: i.role == "mutant").mutant = True
    player_who(lambda i: i.role == "mutant").genome = "Weak"

    for i in range(game.num_weak):
        tomodify = random.choice([i for i in players.values() if i.genome == "Normal" and i.role not in [None, "mutant", "doctor"]])
        tomodify.genome = "Weak"

    for i in range(game.num_resistant):
        tomodify = random.choice([i for i in players.values() if i.genome == "Normal" and i.role not in [None, "mutant", "doctor"]])
        tomodify.genome = "Resistant"

modify()


def get(prompt: str):
    return input(f"{prompt} ").lower()

def get_player(prompt: str) -> Player:
    name = get(prompt)

    if name == "":
        return players["blank"]

    try:
        return players[name]
    except KeyError:
        pass

    for i in players:
        if i.startswith(name):
            return players[i]

    print("Player not found")
    return get_player(prompt)


def kill(player: Player):
    player.dead = True
    gm(f"{player.name} was killed, they were {player.role}")

def gm(message: str = ""):
    print(message)

def role(func=None, *, doctor=False, mutant=False):
    def wrapper(func):
        rolename = func.__name__
        if doctor:
            doctors = [i for i in players.values() if i.role == "doctor" and i.dead == False and i.mutant == False and i.paralized == False]
            doctor_string = " and ".join([i.name for i in doctors])
            gm()
            gm(f"[reverse underline]=== {rolename} ({doctor_string}) ===")
        elif mutant:
            mutants = [i for i in players.values() if i.mutant and i.dead == False]
            mutant_string = ", ".join([i.name for i in mutants])
            gm()
            gm(f"[reverse underline]=== {rolename} ({mutant_string}) ===")
        else:
            gm(f"[reverse underline]=== {rolename} ({player_who(lambda i: i.role == rolename).name}) ===")

        def check_can_play():
            if doctor or mutant:
                return True

            try:
                player = player_who(lambda i: i.role == rolename)
            except StopIteration:
                gm("Role not in game")
                return False

            if player.dead:
                gm("Dead")
                return False
            if player.paralized:
                gm("Paralized")
                return False
            return True

        if not check_can_play():
            return

        func()

    def decorator(func):
        try:
            wrapper(func)
        finally:
            input()

    return decorator if func is None else decorator(func)

def night():
    @role(mutant=True)
    def mutant():
        is_kill = get("Infect or kill?").startswith("k")
        if is_kill:
            kill(get_player("Who to kill?"))
            return

        get_player("Who to paralyze?").paralized = True

        infected = get_player("Who to infect?")
        infected.spyed.mutated = True

        if infected.genome == "Resistant":
            gm("Mutation failed")
        else:
            gm("Mutation successful")
            infected.mutant = True




    @role(doctor=True)
    def doctor():
        is_kill = get("Heal or kill?").startswith("k")
        if is_kill:
            kill(get_player("Who to kill?"))
            return
        
        num_doctors = len([i for i in players.values() if i.role == "doctor" and i.dead == False and i.mutant == False and i.paralized == False])
        for i in range(num_doctors):
            healed = get_player("Who to heal?")
            healed.spyed.healed = True
            if healed.genome == "Weak" and healed.mutant:
                gm("Healing failed")
            else:
                gm("Healing successful")
                healed.mutant = False

    hacker_info = {PSYCHOLOGIST: None, GENETICIST: None, TECHNICIAN: None}

    @role
    def technician():
        info = f"Number of mutants: {len([i for i in players.values() if i.mutant])}"
        hacker_info[TECHNICIAN] = info
        gm(info)

    @role
    def psychologist():
        psychologized = get_player("Who to psychologize?")
        psychologized.spyed.psychologized = True
        info = f"{psychologized.name}, mutant: {psychologized.mutant}"
        hacker_info[PSYCHOLOGIST] = info
        gm(info)

    @role
    def geneticist():
        geneticized = get_player("Who to geneticize?")
        geneticized.spyed.geneticized = True
        info = f"{geneticized.name}, genome: {geneticized.genome}"
        hacker_info[GENETICIST] = info
        gm(info)


    @role
    def hacker():
        def check_role(role):
            if role == "":
                return None
            try:
                return next(i for i in [PSYCHOLOGIST, GENETICIST, TECHNICIAN] if typing.get_args(i)[0].startswith(role))
            except StopIteration:
                return None
        while not (role := check_role(get("Role to hack?"))):
            pass
        gm(f"{hacker_info[role]}")

    @role
    def spy():
        spied = get_player("Who to spy?")
        for (field, value) in spied.spyed:
            gm(f"{field}: {value}")


chief = None
def day():
    global chief
    if chief is None or chief.dead:
        chief = get_player("Who is the chief?")

    kill(get_player("Who to vote against?"))

def show_roles():
    global chief
    gm("Chief: " + chief.name if chief is not None else "No chief")
    gm(tabulate([[j[1] for j in i] for i in players.values()], headers=Player.model_fields))

for i in count():
    gm()
    gm()
    show_roles()

    gm()
    gm()
    gm(f"[bold]Night {i}")
    night()

    gm()
    gm()
    show_roles()

    for p in players.values():
        p.paralized = False
        p.spyed = Player.Spyed()


    gm()
    gm()
    gm(f"[bold]Day {i}")
    day()

