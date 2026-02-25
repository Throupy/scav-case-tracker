import click
from flask.cli import with_appcontext


def register_commands(app):
    app.cli.add_command(create_superuser)
    app.cli.add_command(promote_superuser)
    app.cli.add_command(reassign_discord_cases)


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


@click.command("reassign-discord-cases")
@click.argument("target_username")
@with_appcontext
def reassign_discord_cases(target_username):
    """Reassign all 'Discord Bot' cases to TARGET_USERNAME."""
    from app.extensions import db
    from app.models import User, ScavCase

    bot_user = User.query.filter_by(username="Discord Bot").first()
    if not bot_user:
        click.echo("Error: 'Discord Bot' user not found.", err=True)
        return

    target_user = User.query.filter_by(username=target_username).first()
    if not target_user:
        click.echo(f"Error: user '{target_username}' not found.", err=True)
        return

    count = ScavCase.query.filter_by(user_id=bot_user.id).count()
    if count == 0:
        click.echo("No cases found under 'Discord Bot'.")
        return

    ScavCase.query.filter_by(user_id=bot_user.id).update({"user_id": target_user.id})
    db.session.commit()
    click.echo(f"Reassigned {count} case(s) from 'Discord Bot' to '{target_username}'.")
