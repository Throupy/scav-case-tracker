import click
from flask.cli import with_appcontext


def register_commands(app):
    app.cli.add_command(create_superuser)
    app.cli.add_command(promote_superuser)


@click.command("create-superuser")
@click.option("--username", prompt=True, help="Username for the new superuser account")
@click.option(
    "--password",
    prompt=True,
    hide_input=True,
    confirmation_prompt=True,
    help="Password for the new superuser account",
)
@with_appcontext
def create_superuser(username, password):
    """Create a new superuser account (one-time bootstrap command)."""
    from app.extensions import db, bcrypt
    from app.models import User

    if User.query.filter_by(username=username).first():
        click.echo(f"Error: a user with username '{username}' already exists.", err=True)
        return

    hashed = bcrypt.generate_password_hash(password).decode("utf-8")
    user = User(username=username, password=hashed, is_superuser=True)
    db.session.add(user)
    db.session.commit()
    click.echo(f"Superuser '{username}' created successfully.")


@click.command("promote-superuser")
@click.argument("username")
@with_appcontext
def promote_superuser(username):
    """Promote an existing user to superuser by USERNAME."""
    from app.extensions import db
    from app.models import User

    user = User.query.filter_by(username=username).first()
    if not user:
        click.echo(f"Error: no user found with username '{username}'.", err=True)
        return
    if user.is_superuser:
        click.echo(f"'{username}' is already a superuser.")
        return
    user.is_superuser = True
    db.session.commit()
    click.echo(f"'{username}' has been promoted to superuser.")
