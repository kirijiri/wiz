# :coding: utf-8

import json
import os
import os.path
import types
import requests
import pytest

import wiz.registry
import wiz.filesystem
import wiz.exception


@pytest.fixture()
def mocked_remove(mocker):
    """Return mocked 'os.remove' function."""
    return mocker.patch.object(os, "remove")


@pytest.fixture()
def mocked_export_definition(mocker):
    """Return mocked 'wiz.export_definition' function."""
    return mocker.patch.object(wiz, "export_definition")


@pytest.fixture()
def mocked_fetch_definition_mapping(mocker):
    """Return mocked 'wiz.fetch_definition_mapping' function."""
    return mocker.patch.object(wiz, "fetch_definition_mapping")


@pytest.fixture()
def mocked_fetch_definition(mocker):
    """Return mocked 'wiz.fetch_definition' function."""
    return mocker.patch.object(wiz, "fetch_definition")


@pytest.fixture()
def mocked_filesystem_accessible(mocker):
    """Return mocked 'wiz.filesystem.is_accessible' function."""
    return mocker.patch.object(wiz.filesystem, "is_accessible")


@pytest.fixture()
def mocked_filesystem_get_name(mocker):
    """Return mocked 'wiz.filesystem.get_name' function."""
    return mocker.patch.object(wiz.filesystem, "get_name")


@pytest.fixture()
def mocked_user_home(mocker, temporary_directory):
    """Return mocked local home path."""
    mocker.patch.object(
        os.path, "expanduser", return_value=temporary_directory
    )
    return temporary_directory


@pytest.fixture()
def mocked_local(mocker):
    """Return mocked local registry path."""
    return mocker.patch.object(
        wiz.registry, "get_local", return_value="/usr/people/me/.wiz/registry"
    )


@pytest.fixture()
def mocked_discover(mocker):
    """Return mocked working directory registry paths."""
    paths = [
        "/jobs/ads/project/.common/wiz/registry",
        "/jobs/ads/project/identity/shot/.common/wiz/registry",
    ]
    return mocker.patch.object(
        wiz.registry, "discover", return_value=(path for path in paths)
    )


@pytest.fixture()
def mocked_requests_get(mocker):
    """Return mocked 'requests.get' function."""
    return mocker.patch.object(requests, "get")


@pytest.fixture()
def mocked_requests_post(mocker):
    """Return mocked 'requests.post' function."""
    return mocker.patch.object(requests, "post")


@pytest.fixture()
def mocked_definitions():
    """Return mocked simple definition list."""
    return [
        wiz.definition.Definition({
            "identifier": "foo",
            "version": "0.1.0",
        }),
        wiz.definition.Definition({
            "identifier": "bar",
        }),
        wiz.definition.Definition({
            "identifier": "baz",
            "version": "2.5.1",
        }),
    ]


@pytest.mark.usefixtures("mocked_user_home")
def test_get_local_unreachable():
    """Return local registry."""
    assert wiz.registry.get_local() is None


def test_get_defaults():
    """Return default registries."""
    assert wiz.registry.get_defaults() == [
        os.path.join(
            os.sep, "mill3d", "server", "apps", "WIZ", "registry",
            "primary", "default"
        ),
        os.path.join(
            os.sep, "mill3d", "server", "apps", "WIZ", "registry",
            "secondary", "default"
        ),
        os.path.join(os.sep, "jobs", ".wiz", "registry", "default")
    ]


def test_discover(mocked_filesystem_accessible):
    """Discover registries under paths."""
    mocked_filesystem_accessible.side_effect = [False, True, False, True]

    prefix = os.path.join(os.sep, "jobs", "ads")
    path = os.path.join(prefix, "project", "identity", "shot", "animation")
    registries = wiz.registry.discover(path)

    end = os.path.join(".wiz", "registry")

    assert isinstance(registries, types.GeneratorType)
    assert list(registries) == [
        os.path.join(prefix, "project", "identity", end),
        os.path.join(prefix, "project", "identity", "shot", "animation", end)
    ]

    assert mocked_filesystem_accessible.call_count == 4
    mocked_filesystem_accessible.assert_any_call(
        os.path.join(prefix, "project", end),
    )
    mocked_filesystem_accessible.assert_any_call(
        os.path.join(prefix, "project", "identity", end),
    )
    mocked_filesystem_accessible.assert_any_call(
        os.path.join(prefix, "project", "identity", "shot", end),
    )
    mocked_filesystem_accessible.assert_any_call(
        os.path.join(prefix, "project", "identity", "shot", "animation", end),
    )


def test_discover_fail(mocked_filesystem_accessible):
    """Fail to discover registries under paths not in /jobs/ads."""
    mocked_filesystem_accessible.side_effect = [False, True, False, True]

    prefix = os.path.join(os.sep, "somewhere", "else")
    path = os.path.join(prefix, "project", "identity", "shot", "animation")
    registries = wiz.registry.discover(path)

    assert isinstance(registries, types.GeneratorType)
    assert list(registries) == []

    mocked_filesystem_accessible.assert_not_called()


@pytest.mark.parametrize("options, paths, expected", [
    (
        {},
        ["/path/to/registry1", "path/to/registry2"],
        [
            "/path/to/registry1",
            os.path.join(os.getcwd(), "path/to/registry2"),
            "/jobs/ads/project/.common/wiz/registry",
            "/jobs/ads/project/identity/shot/.common/wiz/registry",
            "/usr/people/me/.wiz/registry"
        ]
    ),
    (
        {"include_local": False},
        ["/path/to/registry1", "path/to/registry2"],
        [
            "/path/to/registry1",
            os.path.join(os.getcwd(), "path/to/registry2"),
            "/jobs/ads/project/.common/wiz/registry",
            "/jobs/ads/project/identity/shot/.common/wiz/registry"
        ]
    ),
    (
        {"include_working_directory": False},
        ["/path/to/registry1", "path/to/registry2"],
        [
            "/path/to/registry1",
            os.path.join(os.getcwd(), "path/to/registry2"),
            "/usr/people/me/.wiz/registry"
        ]
    ),
    (
        {"include_local": False, "include_working_directory": False},
        ["/path/to/registry1", os.path.join(os.getcwd(), "path/to/registry2")],
        ["/path/to/registry1", os.path.join(os.getcwd(), "path/to/registry2")]
    )
], ids=[
    "default",
    "without-local",
    "without-cwd",
    "without-local-nor-cwd",
])
@pytest.mark.usefixtures("mocked_local")
@pytest.mark.usefixtures("mocked_discover")
def test_fetch(mocked_filesystem_accessible, options, paths, expected):
    """Fetch the registries."""
    mocked_filesystem_accessible.return_value = True
    assert wiz.registry.fetch(paths, **options) == expected


@pytest.mark.usefixtures("mocked_discover")
def test_fetch_unreachable_local(mocked_filesystem_accessible, mocked_local):
    mocked_filesystem_accessible.return_value = True
    mocked_local.return_value = None

    paths = ["/path/to/registry1", "path/to/registry2"]
    assert wiz.registry.fetch(paths) == [
        "/path/to/registry1",
        os.path.join(os.getcwd(), "path/to/registry2"),
        "/jobs/ads/project/.common/wiz/registry",
        "/jobs/ads/project/identity/shot/.common/wiz/registry"
    ]


@pytest.mark.usefixtures("mocked_discover")
@pytest.mark.usefixtures("mocked_local")
def test_fetch_unreachable_paths(mocked_filesystem_accessible):
    mocked_filesystem_accessible.side_effect = [True, False]

    paths = ["/path/to/registry1", "path/to/registry2"]
    assert wiz.registry.fetch(paths) == [
        "/path/to/registry1",
        "/jobs/ads/project/.common/wiz/registry",
        "/jobs/ads/project/identity/shot/.common/wiz/registry",
        "/usr/people/me/.wiz/registry"
    ]


def test_install_to_path(
    temporary_directory, mocked_definitions, mocked_fetch_definition_mapping,
    mocked_fetch_definition, mocked_export_definition, mocked_remove, logger,
):
    """Install definitions to path."""
    mocked_fetch_definition_mapping.return_value = "__MAPPING__"
    mocked_fetch_definition.side_effect = wiz.exception.RequestNotFound()

    wiz.registry.install_to_path(
        mocked_definitions, temporary_directory
    )

    registry_path = os.path.join(temporary_directory, ".wiz", "registry")

    mocked_fetch_definition_mapping.assert_called_once_with([registry_path])

    assert mocked_fetch_definition.call_count == 3
    mocked_fetch_definition.assert_any_call("foo==0.1.0", "__MAPPING__")
    mocked_fetch_definition.assert_any_call("bar", "__MAPPING__")
    mocked_fetch_definition.assert_any_call("baz==2.5.1", "__MAPPING__")

    mocked_remove.assert_not_called()

    assert mocked_export_definition.call_count == 3
    mocked_export_definition.assert_any_call(
        registry_path, mocked_definitions[0], overwrite=True
    )
    mocked_export_definition.assert_any_call(
        registry_path, mocked_definitions[1], overwrite=True
    )
    mocked_export_definition.assert_any_call(
        registry_path, mocked_definitions[2], overwrite=True
    )

    logger.info.assert_called_once_with(
        "Successfully installed 3 definition(s) to registry '{}'."
        .format(registry_path)
    )


def test_install_to_path_with_full_registry_path(
    temporary_directory, mocked_definitions, mocked_fetch_definition_mapping,
    mocked_fetch_definition, mocked_export_definition, mocked_remove, logger,
):
    """Install definitions to full registry path."""
    registry_path = os.path.join(temporary_directory, ".wiz", "registry")
    os.makedirs(registry_path)

    mocked_fetch_definition_mapping.return_value = "__MAPPING__"
    mocked_fetch_definition.side_effect = wiz.exception.RequestNotFound()

    wiz.registry.install_to_path(
        mocked_definitions, registry_path
    )

    registry_path = os.path.join(temporary_directory, ".wiz", "registry")

    mocked_fetch_definition_mapping.assert_called_once_with([registry_path])

    assert mocked_fetch_definition.call_count == 3
    mocked_fetch_definition.assert_any_call("foo==0.1.0", "__MAPPING__")
    mocked_fetch_definition.assert_any_call("bar", "__MAPPING__")
    mocked_fetch_definition.assert_any_call("baz==2.5.1", "__MAPPING__")

    mocked_remove.assert_not_called()

    assert mocked_export_definition.call_count == 3
    mocked_export_definition.assert_any_call(
        registry_path, mocked_definitions[0], overwrite=True
    )
    mocked_export_definition.assert_any_call(
        registry_path, mocked_definitions[1], overwrite=True
    )
    mocked_export_definition.assert_any_call(
        registry_path, mocked_definitions[2], overwrite=True
    )

    logger.info.assert_called_once_with(
        "Successfully installed 3 definition(s) to registry '{}'."
        .format(registry_path)
    )


def test_install_to_path_with_relative_path(
    temporary_directory, mocked_definitions, mocked_fetch_definition_mapping,
    mocked_fetch_definition, mocked_export_definition, mocked_remove, logger,
):
    """Install definitions to relative registry path."""
    path = os.path.join(temporary_directory, "path", "..", "foo")
    os.makedirs(path)

    mocked_fetch_definition_mapping.return_value = "__MAPPING__"
    mocked_fetch_definition.side_effect = wiz.exception.RequestNotFound()

    wiz.registry.install_to_path(
        mocked_definitions, path
    )

    registry_path = os.path.join(temporary_directory, "foo", ".wiz", "registry")

    mocked_fetch_definition_mapping.assert_called_once_with([registry_path])

    assert mocked_fetch_definition.call_count == 3
    mocked_fetch_definition.assert_any_call("foo==0.1.0", "__MAPPING__")
    mocked_fetch_definition.assert_any_call("bar", "__MAPPING__")
    mocked_fetch_definition.assert_any_call("baz==2.5.1", "__MAPPING__")

    mocked_remove.assert_not_called()

    assert mocked_export_definition.call_count == 3
    mocked_export_definition.assert_any_call(
        registry_path, mocked_definitions[0], overwrite=True
    )
    mocked_export_definition.assert_any_call(
        registry_path, mocked_definitions[1], overwrite=True
    )
    mocked_export_definition.assert_any_call(
        registry_path, mocked_definitions[2], overwrite=True
    )

    logger.info.assert_called_once_with(
        "Successfully installed 3 definition(s) to registry '{}'."
        .format(registry_path)
    )


def test_install_to_path_error_path(
    temporary_directory, mocked_definitions, mocked_fetch_definition_mapping,
    mocked_fetch_definition, mocked_export_definition, mocked_remove, logger,
):
    """Fail to install definitions when path is incorrect."""
    registry_path = os.path.join(temporary_directory, "somewhere")

    with pytest.raises(wiz.exception.InstallError) as error:
        wiz.registry.install_to_path(mocked_definitions, registry_path)

    mocked_remove.assert_not_called()
    mocked_fetch_definition_mapping.assert_not_called()
    mocked_fetch_definition.assert_not_called()
    mocked_export_definition.assert_not_called()
    logger.info.assert_not_called()

    assert (
        "{!r} is not a valid registry directory.".format(registry_path)
    ) in str(error)


def test_install_to_path_error_definition_exists(
    temporary_directory, mocked_definitions, mocked_fetch_definition_mapping,
    mocked_fetch_definition, mocked_export_definition, mocked_remove, logger,
):
    """Fail to install definitions when definition exists."""
    mocked_fetch_definition_mapping.return_value = "__MAPPING__"
    mocked_fetch_definition.side_effect = [
        wiz.exception.RequestNotFound(),
        wiz.definition.Definition({
            "identifier": "bar",
            "definition-location": "/path/to/registry/bar/bar.json",
            "registry": "/path/to/registry"
        }),
        wiz.definition.Definition({
            "identifier": "baz",
            "version": "2.5.1",
            "description": "test",
            "definition-location": "/path/to/registry/baz/baz-2.5.1.json",
            "registry": "/path/to/registry"
        }),
    ]

    with pytest.raises(wiz.exception.DefinitionsExist) as error:
        wiz.registry.install_to_path(mocked_definitions, temporary_directory)

    registry_path = os.path.join(temporary_directory, ".wiz", "registry")
    mocked_fetch_definition_mapping.assert_called_once_with([registry_path])

    assert mocked_fetch_definition.call_count == 3
    mocked_fetch_definition.assert_any_call("foo==0.1.0", "__MAPPING__")
    mocked_fetch_definition.assert_any_call("bar", "__MAPPING__")
    mocked_fetch_definition.assert_any_call("baz==2.5.1", "__MAPPING__")

    mocked_remove.assert_not_called()
    mocked_export_definition.assert_not_called()
    logger.info.assert_not_called()

    assert (
        "DefinitionsExist: 1 definition(s) already exist in registry."
    ) in str(error)


def test_install_to_path_overwrite(
    temporary_directory, mocked_definitions, mocked_fetch_definition_mapping,
    mocked_fetch_definition, mocked_export_definition, mocked_remove, logger,
):
    """Install definitions while overwriting existing definitions."""
    mocked_fetch_definition_mapping.return_value = "__MAPPING__"
    mocked_fetch_definition.side_effect = [
        wiz.exception.RequestNotFound(),
        wiz.definition.Definition({
            "identifier": "bar",
            "definition-location": "/path/to/registry/bar/bar.json",
            "registry": "/path/to/registry"
        }),
        wiz.definition.Definition({
            "identifier": "baz",
            "version": "2.5.1",
            "description": "test",
            "definition-location": "/path/to/registry/baz/baz-2.5.1.json",
            "registry": "/path/to/registry"
        }),
    ]

    wiz.registry.install_to_path(
        mocked_definitions, temporary_directory, overwrite=True
    )

    registry_path = os.path.join(temporary_directory, ".wiz", "registry")
    mocked_fetch_definition_mapping.assert_called_once_with([registry_path])

    assert mocked_fetch_definition.call_count == 3
    mocked_fetch_definition.assert_any_call("foo==0.1.0", "__MAPPING__")
    mocked_fetch_definition.assert_any_call("bar", "__MAPPING__")
    mocked_fetch_definition.assert_any_call("baz==2.5.1", "__MAPPING__")

    mocked_remove.assert_called_once_with(
        "/path/to/registry/baz/baz-2.5.1.json"
    )

    assert mocked_export_definition.call_count == 2
    mocked_export_definition.assert_any_call(
        registry_path, mocked_definitions[0], overwrite=True
    )
    mocked_export_definition.assert_any_call(
        "/path/to/registry/baz", mocked_definitions[2], overwrite=True
    )

    logger.info.assert_called_once_with(
        "Successfully installed 2 definition(s) to registry '{}'."
        .format(registry_path)
    )


def test_install_to_path_no_content(
    temporary_directory, mocked_definitions, mocked_fetch_definition_mapping,
    mocked_fetch_definition, mocked_export_definition, mocked_remove, logger,
):
    """Fail to install definitions when no new content available."""
    mocked_fetch_definition_mapping.return_value = "__MAPPING__"
    mocked_fetch_definition.side_effect = mocked_definitions

    with pytest.raises(wiz.exception.InstallNoChanges) as error:
        wiz.registry.install_to_path(mocked_definitions, temporary_directory)

    registry_path = os.path.join(temporary_directory, ".wiz", "registry")
    mocked_fetch_definition_mapping.assert_called_once_with([registry_path])

    assert mocked_fetch_definition.call_count == 3
    mocked_fetch_definition.assert_any_call("foo==0.1.0", "__MAPPING__")
    mocked_fetch_definition.assert_any_call("bar", "__MAPPING__")
    mocked_fetch_definition.assert_any_call("baz==2.5.1", "__MAPPING__")

    mocked_remove.assert_not_called()
    mocked_export_definition.assert_not_called()
    logger.info.assert_not_called()

    assert "InstallNoChanges: Nothing to install." in str(error)


@pytest.mark.parametrize("options, overwrite", [
    ({}, "false"),
    ({"overwrite": True}, "true"),
], ids=[
    "no-options",
    "with-overwrite",
])
def test_install_to_vcs(
    mocked_requests_get, mocked_requests_post, mocked_definitions,
    mocked_filesystem_get_name, logger, monkeypatch, mocker, options, overwrite
):
    """Install definitions to vault registry."""
    monkeypatch.setenv("WIZ_SERVER", "https://wiz.themill.com")
    reload(wiz.symbol)

    mocked_requests_get.return_value = mocker.Mock(
        ok=True, **{
            "json.return_value": {
                "data": {
                    "content": {
                        "registry-id": {
                            "identifier": "registry-id",
                            "description": "This is a registry",
                            "avatar_url": "/project/registry-id/avatar",
                        }
                    }
                }
            }
        }
    )
    mocked_requests_post.return_value = mocker.Mock(ok=True)
    mocked_filesystem_get_name.return_value = "John Doe"

    wiz.registry.install_to_vcs(mocked_definitions, "registry-id", **options)

    mocked_requests_get.assert_called_once_with(
        "https://wiz.themill.com/api/registry/all"
    )

    mocked_requests_post.assert_called_once_with(
        "https://wiz.themill.com/api/registry/registry-id/release",
        params={"overwrite": overwrite},
        data={
            "contents": json.dumps([
                definition.encode() for definition in mocked_definitions
            ]),
            "author": "John Doe"
        }
    )

    mocked_filesystem_get_name.assert_called_once()

    logger.info.assert_called_once_with(
        "Successfully installed 3 definition(s) to registry 'registry-id'."
    )


@pytest.mark.parametrize("json_response, expected_error", [
    ({"error": {"message": "Oh Shit!"}}, "Oh Shit!"),
    ({}, "unknown"),
], ids=[
    "with-json-error",
    "without-json-error",
])
def test_install_to_vcs_error_get(
    mocked_requests_get, mocked_requests_post, mocked_definitions,
    mocked_filesystem_get_name, logger, monkeypatch, mocker, json_response,
    expected_error
):
    """Fail to install definitions when fetching process failed."""
    monkeypatch.setenv("WIZ_SERVER", "https://wiz.themill.com")
    reload(wiz.symbol)

    mocked_requests_get.return_value = mocker.Mock(
        ok=False, **{"json.return_value": json_response}
    )

    with pytest.raises(wiz.exception.InstallError) as error:
        wiz.registry.install_to_vcs(mocked_definitions, "registry-id")

    mocked_requests_get.assert_called_once_with(
        "https://wiz.themill.com/api/registry/all"
    )

    mocked_requests_post.assert_not_called()
    mocked_filesystem_get_name.assert_not_called()
    logger.info.assert_not_called()

    assert (
        "VCS registries could not be retrieved: {}".format(expected_error)
    ) in str(error)


@pytest.mark.parametrize("json_response", [
    {"data": {"content": {}}}, {}
], ids=[
    "with-json-error",
    "without-json-error",
])
def test_install_to_vcs_error_incorrect_identifier(
    mocked_requests_get, mocked_requests_post, mocked_definitions,
    mocked_filesystem_get_name, logger, monkeypatch, mocker, json_response
):
    """Fail to install definitions when registry identifier is incorrect."""
    monkeypatch.setenv("WIZ_SERVER", "https://wiz.themill.com")
    reload(wiz.symbol)

    mocked_requests_get.return_value = mocker.Mock(
        ok=True, **{"json.return_value": json_response}
    )

    with pytest.raises(wiz.exception.InstallError) as error:
        wiz.registry.install_to_vcs(mocked_definitions, "registry-id")

    mocked_requests_get.assert_called_once_with(
        "https://wiz.themill.com/api/registry/all"
    )

    mocked_requests_post.assert_not_called()
    mocked_filesystem_get_name.assert_not_called()
    logger.info.assert_not_called()

    assert "'registry-id' is not a valid registry" in str(error)


def test_install_to_vcs_error_definition_exists(
    mocked_requests_get, mocked_requests_post, mocked_definitions,
    mocked_filesystem_get_name, logger, monkeypatch, mocker
):
    """Fail to install definition when definition exists."""
    monkeypatch.setenv("WIZ_SERVER", "https://wiz.themill.com")
    reload(wiz.symbol)

    mocked_requests_get.return_value = mocker.Mock(
        ok=True, **{
            "json.return_value": {
                "data": {
                    "content": {
                        "registry-id": {
                            "identifier": "registry-id",
                            "description": "This is a registry",
                            "avatar_url": "/project/registry-id/avatar",
                        }
                    }
                }
            }
        }
    )

    mocked_requests_post.return_value = mocker.Mock(
        ok=False, status_code=409, **{
            "json.return_value": {
                "error": {
                    "code": 409,
                    "definitions": ["def_A"]
                }
            }
        }
    )
    mocked_filesystem_get_name.return_value = "John Doe"

    with pytest.raises(wiz.exception.DefinitionsExist) as error:
        wiz.registry.install_to_vcs(mocked_definitions, "registry-id")

    mocked_requests_get.assert_called_once_with(
        "https://wiz.themill.com/api/registry/all"
    )

    mocked_requests_post.assert_called_once_with(
        "https://wiz.themill.com/api/registry/registry-id/release",
        params={"overwrite": "false"},
        data={
            "contents": json.dumps([
                definition.encode() for definition in mocked_definitions
            ]),
            "author": "John Doe"
        }
    )

    mocked_filesystem_get_name.assert_called_once()
    logger.info.assert_not_called()

    assert (
        "DefinitionsExist: 1 definition(s) already exist in registry."
    ) in str(error)


@pytest.mark.parametrize("json_response, expected_error", [
    ({"error": {"message": "Oh Shit!"}}, "Oh Shit!"),
    ({}, "unknown"),
], ids=[
    "with-json-error",
    "without-json-error",
])
def test_install_to_vcs_error_post(
    mocked_requests_get, mocked_requests_post, mocked_definitions,
    mocked_filesystem_get_name, logger, monkeypatch, mocker, json_response,
    expected_error
):
    """Fail to install definition when release post failed."""
    monkeypatch.setenv("WIZ_SERVER", "https://wiz.themill.com")
    reload(wiz.symbol)

    mocked_requests_get.return_value = mocker.Mock(
        ok=True, **{
            "json.return_value": {
                "data": {
                    "content": {
                        "registry-id": {
                            "identifier": "registry-id",
                            "description": "This is a registry",
                            "avatar_url": "/project/registry-id/avatar",
                        }
                    }
                }
            }
        }
    )

    mocked_requests_post.return_value = mocker.Mock(
        ok=False, status_code=500, **{"json.return_value": json_response}
    )
    mocked_filesystem_get_name.return_value = "John Doe"

    with pytest.raises(wiz.exception.InstallError) as error:
        wiz.registry.install_to_vcs(mocked_definitions, "registry-id")

    mocked_requests_get.assert_called_once_with(
        "https://wiz.themill.com/api/registry/all"
    )

    mocked_requests_post.assert_called_once_with(
        "https://wiz.themill.com/api/registry/registry-id/release",
        params={"overwrite": "false"},
        data={
            "contents": json.dumps([
                definition.encode() for definition in mocked_definitions
            ]),
            "author": "John Doe"
        }
    )

    mocked_filesystem_get_name.assert_called_once()
    logger.info.assert_not_called()

    print(str(error))
    assert (
        "Definitions could not be installed to registry 'registry-id' "
        "[{}]".format(expected_error)
    ) in str(error)


def test_install_to_vcs_no_content(
    mocked_requests_get, mocked_requests_post, mocked_definitions,
    mocked_filesystem_get_name, logger, monkeypatch, mocker
):
    """Fail to install definitions when no new content available."""
    monkeypatch.setenv("WIZ_SERVER", "https://wiz.themill.com")
    reload(wiz.symbol)

    mocked_requests_get.return_value = mocker.Mock(
        ok=True, **{
            "json.return_value": {
                "data": {
                    "content": {
                        "registry-id": {
                            "identifier": "registry-id",
                            "description": "This is a registry",
                            "avatar_url": "/project/registry-id/avatar",
                        }
                    }
                }
            }
        }
    )

    mocked_requests_post.return_value = mocker.Mock(ok=False, status_code=417)
    mocked_filesystem_get_name.return_value = "John Doe"

    with pytest.raises(wiz.exception.InstallNoChanges) as error:
        wiz.registry.install_to_vcs(mocked_definitions, "registry-id")

    mocked_requests_get.assert_called_once_with(
        "https://wiz.themill.com/api/registry/all"
    )

    mocked_requests_post.assert_called_once_with(
        "https://wiz.themill.com/api/registry/registry-id/release",
        params={"overwrite": "false"},
        data={
            "contents": json.dumps([
                definition.encode() for definition in mocked_definitions
            ]),
            "author": "John Doe"
        }
    )

    mocked_filesystem_get_name.assert_called_once()
    logger.info.assert_not_called()

    assert "InstallNoChanges: Nothing to install." in str(error)
