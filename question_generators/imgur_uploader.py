import os
from imgurpython import ImgurClient
import click


def get_config():
    client_id = os.environ.get("IMGUR_API_ID")
    client_secret = os.environ.get("IMGUR_API_SECRET")
    data = {"id": client_id, "secret": client_secret}
    return data


@click.command()
@click.argument("image", type=click.Path(exists=True))
def upload_image(image):
    """Uploads an image file to Imgur"""
    config = get_config()

    if not config:
        click.echo(
            "Cannot upload - could not find IMGUR_API_ID or " "IMGUR_API_SECRET environment variables or config file"
        )
        return
    client = ImgurClient(config["id"], config["secret"])
    anon = True
    click.echo("Uploading file {}".format(click.format_filename(image)))

    response = client.upload_from_path(image, anon=anon)
    click.echo("File uploaded - see your image at {}".format(response["link"]))


if __name__ == "__main__":
    upload_image()
