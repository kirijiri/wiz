# :coding: utf-8

import os
import json
import requests

import mlog

import wiz.history
import wiz.symbol
import wiz.filesystem


def get_local():
    """Return the local registry if available."""
    registry_path = os.path.join(os.path.expanduser("~"), ".wiz", "registry")
    if os.path.isdir(registry_path) and os.access(registry_path, os.R_OK):
        return registry_path


def get_defaults():
    """Return the default registries."""
    server_root = os.path.join(os.sep, "mill3d", "server", "apps", "WIZ")

    return [
        os.path.join(server_root, "registry", "primary", "default"),
        os.path.join(server_root, "registry", "secondary", "default"),
        os.path.join(os.sep, "jobs", ".wiz", "registry", "default")
    ]


def fetch(paths, include_local=True, include_working_directory=True):
    """Fetch all registries from *paths*.

    *include_local* indicates whether the local registry should be included.

    *include_working_directory* indicates whether the current working directory
    should be parsed to discover registry folders.

    """
    registries = []

    for path in paths:
        if not wiz.filesystem.is_accessible(path):
            continue
        registries.append(path)

    if include_working_directory:
        for registry_path in discover(os.getcwd()):
            registries.append(registry_path)

    registry_path = get_local()
    if registry_path and include_local:
        registries.append(registry_path)

    return registries


def discover(path):
    """Yield available registry folders from *path* folder hierarchy.

    Each folder constituting the hierarchy of *path* are parsed so that
    existing :file:`.wiz/registry` folders can be yield from the deepest
    to the closest.

    Example::

        >>> list(discover("/jobs/ads/project/identity/shot"))
        [
            "/jobs/ads/project/.wiz/registry",
            "/jobs/ads/project/identity/shot/.wiz/registry"
        ]

    .. important::

        Registry folders can be discovered only under :file:`/jobs/ads`.

    """
    path = os.path.abspath(path)

    # Only discover the registry if the top level hierarchy is /jobs/ads.
    prefix = os.path.join(os.sep, "jobs", "ads")
    if not path.startswith(prefix):
        return

    for folder in path.split(os.sep)[3:]:
        prefix = os.path.join(prefix, folder)
        registry_path = os.path.join(prefix, ".wiz", "registry")

        if wiz.filesystem.is_accessible(registry_path):
            yield registry_path


def install_to_path(
    definition, registry_path, overwrite=False
):
    """Install a definition to a registry on the file system.

    *definition* must be a valid :class:`~wiz.definition.Definition` instance.

    *registry_path* is the target registry path to install to.

    If *overwrite* is True, any existing definitions in the target registry
    will be overwritten.

    Raises :exc:`wiz.exception.IncorrectDefinition` if data in *path* cannot
    create a valid instance of :class:`wiz.definition.Definition`.

    Raises :exc:`wiz.exception.DefinitionExists` if definition already exists in
    the target registry and overwrite is False.

    Raises :exc:`OSError` if the definition can not be exported in
    *registry_path*.

    Raises :exc:`wiz.exception.InstallError` if the target registry path is not
    a valid directory.

    """
    logger = mlog.Logger(__name__ + ".install_to_path")

    if not os.path.isdir(registry_path):
        raise wiz.exception.InstallError(
            "{!r} is not a valid registry directory.".format(registry_path)
        )

    registry_path = os.path.abspath(registry_path)
    if not registry_path.endswith(".wiz/registry"):
        registry_path = os.path.join(registry_path, ".wiz", "registry")

    try:
        wiz.export_definition(registry_path, definition, overwrite=overwrite)

    except wiz.exception.FileExists:
        raise wiz.exception.DefinitionExists(
            "Definition '{identifier}-{version}' already exists.".format(
                identifier=definition.identifier,
                version=definition.version
            )
        )

    logger.info(
        "Successfully installed {identifier}-{version} to "
        "registry {registry!r}.".format(
            identifier=definition.identifier,
            version=definition.version,
            registry=registry_path
        )
    )


def install_to_vcs(
    definition, registry_identifier, overwrite=False
):
    """Install a definition to a repository registry.

    *definition* must be a valid :class:`~wiz.definition.Definition` instance.

    *registry_identifier* is the identifier of the target :term:`Wiz Vault`
    registry to install to.

    If *overwrite* is True, any existing definitions in the target registry
    will be overwritten.

    Raises :exc:`wiz.exception.IncorrectDefinition` if data in *path* cannot
    create a valid instance of :class:`wiz.definition.Definition`.

    Raises :exc:`wiz.exception.DefinitionExists` if definition already exists in
    the target registry and overwrite is False.

    Raises :exc:`wiz.exception.InstallError` if the registry could not be found,
    or definition could not be installed into it.

    """
    logger = mlog.Logger(__name__ + ".install_to_vcs")

    response = requests.get("{}/api/registry/all".format(wiz.symbol.WIZ_SERVER))
    if not response.ok:
        raise wiz.exception.InstallError(
            "Vault registries could not be retrieved: {}".format(
                response.json().get("error", {}).get("message", "unknown")
            )
        )

    registry_identifiers = response.json().get("data", {}).get("content", {})
    if registry_identifier not in registry_identifiers:
        raise wiz.exception.InstallError(
            "{!r} is not a valid registry.".format(registry_identifier)
        )

    response = requests.post(
        "{server}/api/registry/{name}/release".format(
            server=wiz.symbol.WIZ_SERVER,
            name=registry_identifier
        ),
        params={"overwrite": json.dumps(overwrite)},
        data={
            "content": definition.encode(),
            "message": (
                "Add {identifier!r} [{version}] to registry ({username})"
                "\n\nauthor: {name}".format(
                    identifier=definition.get("identifier"),
                    version=definition.get("version"),
                    username=wiz.filesystem.get_username(),
                    name=wiz.filesystem.get_name() or "unknown",
                )
            )
        }
    )

    # Return if all good.
    if response.ok:
        logger.info(
            "Successfully installed {identifier}-{version} to "
            "registry {registry!r}.".format(
                identifier=definition.identifier,
                version=definition.version,
                registry=registry_identifier
            )
        )
        return

    if response.status_code == 409:
        raise wiz.exception.DefinitionExists(
            "Definition '{identifier}-{version}' already exists.".format(
                identifier=definition.identifier,
                version=definition.version
            )
        )

    else:
        raise wiz.exception.InstallError(
            "Definition could not be installed to registry {registry!r}: "
            "{error}".format(
                registry=registry_identifier,
                error=response.json().get("error", {}).get("message", "unknown")
            )
        )
