import click
import logging

from noip.piano import Piano
from noip.asterisk import AMIConnection, AsteriskInstrument
from noip.gamepad import GamepadInstrument, pygame_session, create_gamepad, gamepad_list
from noip.web import HTTPServer


@click.group()
@click.option('--debug/--no-debug', default=False)
@click.option('--device')
@click.pass_context
def cli(ctx, debug, device=None):
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level)
    ctx.obj['device'] = device


@cli.command()
@click.argument("host")
@click.argument("username")
@click.argument("password")
@click.option('--port', default=5038, type=click.INT)
@click.pass_context
def asterisk(ctx, host, username, password, port):
    piano = create_piano(ctx, "NOIP asterisk ({}:{})".format(host, port))
    connection = AMIConnection(host, username, password, port)
    instrument = AsteriskInstrument(piano, connection)

    with connection:
        loop(instrument)


@cli.command()
@click.argument("position", type=click.INT)
@click.pass_context
def gamepad(ctx, position):
    with pygame_session():
        gamepad = create_gamepad(position)
        piano = create_piano(ctx, "NOIP gamepad ({})".format(gamepad.get_name()))
        instrument = GamepadInstrument(piano, gamepad)
        loop(instrument)


@cli.command()
@click.option('--host', default="0.0.0.0")
@click.option('--port', type=click.INT, default=40555)
@click.pass_context
def http(ctx, host, port):
    piano = create_piano(ctx, "NOIP HTTP ({}:{})".format(host, port))
    server = HTTPServer(piano, host=host, port=port)
    with server:
        server.run()


@cli.command()
def list_gamepads():
    with pygame_session():
        for position, name in gamepad_list():
            print("{}: {}".format(position, name))


def create_piano(ctx, name):
    if ctx.obj['device']:
        return Piano.device(ctx.obj['device'])
    return Piano.virtual(name)


def loop(instrument):
    with instrument:
        while instrument.playing():
            instrument.play()


if __name__ == "__main__":
    cli(obj={})
