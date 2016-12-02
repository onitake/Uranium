# Copyright (c) 2016 Ultimaker B.V.
# Uranium is released under the terms of the AGPLv3 or higher.

import pytest
import uuid # For creating unique ID's for each container stack.
import os

from UM.Signal import Signal
from UM.Resources import Resources

import UM.Settings
import UM.Settings.ContainerInterface
import UM.Settings.DefinitionContainer
import UM.Settings.InstanceContainer
import UM.Settings.ContainerStack
from UM.Settings.ContainerStack import IncorrectVersionError
from UM.Settings.ContainerStack import InvalidContainerStackError

##  A fake container class that implements ContainerInterface.
#
#   This allows us to test the container stack independent of any actual
#   implementation of the containers. If something were to go wrong in the
#   actual implementations, the tests in this suite are unaffected.
class MockContainer(UM.Settings.ContainerInterface.ContainerInterface):
    ##  Creates a mock container with a new unique ID.
    def __init__(self):
        self._id = uuid.uuid4().int
        self._metadata = {}
        self.items = {}

    ##  Gets the unique ID of the container.
    #
    #   \return A unique identifier for this container.
    def getId(self):
        return self._id

    ##  Gives an arbitrary name.
    #
    #   \return Some string.
    def getName(self):
        return "Fred"

    ##  Get whether the container item is stored on a read only location in the filesystem.
    #
    #   \return Always returns False
    def isReadOnly(self):
        return False

    ##  Mock get path
    def getPath(self):
        return "/path/to/the/light/side"

    ##  Mock set path
    def setPath(self, path):
        pass

    ##  Returns the metadata dictionary.
    #
    #   \return A dictionary containing metadata for this container stack.
    def getMetaData(self):
        return self._metadata

    ##  Gets an entry from the metadata.
    #
    #   \param entry The entry to get from the metadata.
    #   \param default The default value in case the entry is missing.
    #   \return The value belonging to the requested entry, or the default if no
    #   such key exists.
    def getMetaDataEntry(self, entry, default = None):
        if entry in self._metadata:
            return self._metadata["entry"]
        return default

    ##  Gets the value of a container item property.
    #
    #   If the key doesn't exist, returns None.
    #
    #   \param key The key of the item to get.
    def getProperty(self, key, property_name):
        if key in self.items:
            return self.items[key]
        return None

    propertyChanged = Signal()

    def hasProperty(self, key, property_name):
        return key in self.items

    ##  Serialises this container.
    #
    #   The serialisation of the mock needs to be kept simple, so it only
    #   serialises the ID. This makes the tests succeed if the serialisation
    #   creates different instances (which is desired).
    #
    #   \return A static string representing a container.
    def serialize(self):
        return str(self._id)

    ##  Deserialises a string to a container.
    #
    #   The serialisation of the mock needs to be kept simple, so it only
    #   deserialises the ID. This makes the tests succeed if the serialisation
    #   creates different instances (which is desired).
    #
    #   \param serialized A serialised mock container.
    def deserialize(self, serialized):
        self._id = int(serialized)

##  Creates a brand new container stack to test with.
#
#   The container stack will get a new, unique ID.
@pytest.fixture
def container_stack():
    return UM.Settings.ContainerStack(uuid.uuid4().int)

##  Creates a brand new container registry.
#
#   To force a new container registry, the registry is first set to None and
#   then re-requested.
#
#   \return A brand new container registry.
@pytest.fixture
def container_registry():
    Resources.addSearchPath(os.path.dirname(os.path.abspath(__file__)))
    UM.Settings.ContainerRegistry._ContainerRegistry__instance = None # Reset the private instance variable every time
    UM.PluginRegistry.getInstance().removeType("settings_container")

    return UM.Settings.ContainerRegistry.getInstance()

##  Tests the creation of a container stack.
#
#   The actual creation is done in a fixture though.
#
#   \param container_stack A new container stack from a fixture.
def test_container_stack(container_stack):
    assert container_stack != None

##  Tests adding a container to the stack.
#
#   \param container_stack A new container stack from a fixture.
def test_addContainer(container_stack):
    assert container_stack.getContainers() == [] # First nothing.
    container = MockContainer()
    container_stack.addContainer(container)
    assert container_stack.getContainers() == [container] # Then something!

    with pytest.raises(Exception):
        container_stack.addContainer(container_stack) # Adding itself gives an exception.
    assert container_stack.getContainers() == [container] # Make sure that adding itself didn't change the state, even if it raises an exception.

##  Tests deserialising a container stack from a corrupted string.
def test_deserialize_syntax_error(container_stack):
    serialised = "["
    with pytest.raises(Exception):
        container_stack.deserialize(serialised)

##  Tests deserialising a container stack when the version number is wrong.
#
#   \param container_stack A new container stack from a fixture.
#   \param container_registry A new container registry from a fixture.
def test_deserialize_wrong_version(container_stack, container_registry):
    container_registry.addContainer(UM.Settings.InstanceContainer("a")) # Make sure this container isn't the one it complains about.

    serialised = """[general]
name = Test
id = testid
containers = a
version = -1""" # -1 should always be wrong.
    with pytest.raises(IncorrectVersionError):
        container_stack.deserialize(serialised)

##  Tests deserialising a container stack from files that are missing entries.
#
#   Sorry for the indenting.
#
#   \param container_stack A new container stack from a fixture.
#   \param container_registry A new container registry from a fixture.
def test_deserialize_missing_items(container_stack, container_registry):
    container_registry.addContainer(UM.Settings.InstanceContainer("a")) # Make sure this container isn't the one it complains about.

    serialised_no_name = """[general]
id = testid
containers = a
version = """ + str(UM.Settings.ContainerStack.Version)
    with pytest.raises(InvalidContainerStackError):
        container_stack.deserialize(serialised_no_name)

    serialised_no_id = """[general]
name = Test
containers = a
version = """ + str(UM.Settings.ContainerStack.Version)
    with pytest.raises(InvalidContainerStackError):
        container_stack.deserialize(serialised_no_id)

    serialised_no_version = """[general]
name = Test
id = testid
containers = a"""
    with pytest.raises(InvalidContainerStackError):
        container_stack.deserialize(serialised_no_version)

    serialised_no_containers = """[general]
name = Test
id = testid
version = """ + str(UM.Settings.ContainerStack.Version)
    container_stack.deserialize(serialised_no_containers) # Missing containers is allowed.

    serialised_no_general = """[metadata]
foo = bar"""
    with pytest.raises(InvalidContainerStackError):
        container_stack.deserialize(serialised_no_general)

##  Tests deserialising a container stack with various subcontainers.
#
#   Sorry for the indenting.
#
#   \param container_stack A new container stack from a fixture.
#   \param container_registry A new container registry from a fixture.
def test_deserialize_containers(container_stack, container_registry):
    container = UM.Settings.InstanceContainer("a")
    container_registry.addContainer(container)

    serialised = """[general]
name = Test
id = testid
containers = a
version = """ + str(UM.Settings.ContainerStack.Version) # Test case where there is a container.
    container_stack.deserialize(serialised)
    assert container_stack.getContainers() == [container]

    container_stack = UM.Settings.ContainerStack(uuid.uuid4().int)
    serialised = """[general]
name = Test
id = testid
containers =
version = """ + str(UM.Settings.ContainerStack.Version) # Test case where there is no container.
    container_stack.deserialize(serialised)
    assert container_stack.getContainers() == []

    container_stack = UM.Settings.ContainerStack(uuid.uuid4().int)
    serialised = """[general]
name = Test
id = testid
containers = a,a
version = """ + str(UM.Settings.ContainerStack.Version) # Test case where there are two of the same containers.
    container_stack.deserialize(serialised)
    assert container_stack.getContainers() == [container, container]

    container_stack = UM.Settings.ContainerStack(uuid.uuid4().int)
    serialised = """[general]
name = Test
id = testid
containers = a,b
version = """ + str(UM.Settings.ContainerStack.Version) # Test case where a container doesn't exist.
    with pytest.raises(Exception):
        container_stack.deserialize(serialised)

    container_stack = UM.Settings.ContainerStack(uuid.uuid4().int)
    container_b = UM.Settings.InstanceContainer("b") # Add the missing container and try again.
    UM.Settings.ContainerRegistry.getInstance().addContainer(container_b)
    container_stack.deserialize(serialised)
    assert container_stack.getContainers() == [container, container_b]

##  Individual test cases for test_findContainer.
#
#   Each test case has:
#   * A description for debugging.
#   * A list of dictionaries for containers to search in.
#   * A filter to search with.
#   * A required result.
test_findContainer_data = [
    {
        "description": "Search empty",
        "containers": [
            { },
            { }
        ],
        "filter": { },
        "result": { }
    },
    {
        "description": "Not found",
        "containers": [
            { "foo": "baz" }
        ],
        "filter": { "foo": "bar" },
        "result": None
    },
    {
        "description": "Key not found",
        "containers": [
            { "loo": "bar" }
        ],
        "filter": { "foo": "bar" },
        "result": None
    },
    {
        "description": "Multiple constraints",
        "containers": [
            { "id": "a", "number": 1, "string": "foo", "mixed": 10 },
            { "id": "b", "number": 2, "string": "foo", "mixed": "bar" },
            { "id": "c", "number": 1, "string": "loo", "mixed": 10 }
        ],
        "filter": { "number": 1, "string": "foo", "mixed": 10 },
        "result": { "id": "a", "number": 1, "string": "foo", "mixed": 10 }
    },
    {
        "description": "Wildcard Number",
        "containers": [
            { "id": "a", "string": "foo" },
            { "id": "b", "number": 1 },
            { "id": "c", "number": 2 },
        ],
        "filter": { "number": "*" },
        "result": { "id": "c", "number": 2 }
    },
    {
        "description": "Wildcard String",
        "containers": [
            { "id": "a", "number": 1 },
            { "id": "b", "string": "foo" },
            { "id": "c", "string": "boo" }
        ],
        "filter": { "string": "*" },
        "result": { "id": "c", "string": "boo" }
    }
]

##  Tests finding a container by a filter.
#
#   \param container_stack A new container stack from a fixture.
#   \param data Individual test cases, provided from test_findContainer_data.
@pytest.mark.parametrize("data", test_findContainer_data)
def test_findContainer(container_stack, data):
    for container in data["containers"]: # Add all containers.
        mockup = MockContainer()
        for key, value in container.items(): # Copy the data to the metadata of the mock-up.
            mockup.getMetaData()[key] = value
        container_stack.addContainer(mockup)

    answer = container_stack.findContainer(data["filter"]) # The actual method to test.

    if data["result"] is None:
        assert answer is None
    else:
        assert answer is not None
        assert data["result"] == answer.getMetaData()

##  Tests getting a container by index.
#
#   \param container_stack A new container stack from a fixture.
def test_getContainer(container_stack):
    with pytest.raises(IndexError):
        container_stack.getContainer(0)

    # Fill with data.
    container1 = MockContainer()
    container_stack.addContainer(container1)
    container2 = MockContainer()
    container_stack.addContainer(container2)
    container3 = MockContainer()
    container_stack.addContainer(container3)

    assert container_stack.getContainer(2) == container1
    assert container_stack.getContainer(1) == container2
    assert container_stack.getContainer(0) == container3
    with pytest.raises(IndexError):
        container_stack.getContainer(3)
    with pytest.raises(IndexError):
        container_stack.getContainer(-1)

##  Tests getting and changing the metadata of the container stack.
#
#   \param container_stack A new container stack from a fixture.
def test_getMetaData(container_stack):
    meta_data = container_stack.getMetaData()
    assert meta_data != None

    meta_data["foo"] = "bar" #Try adding an entry.
    assert container_stack.getMetaDataEntry("foo") == "bar"

##  Individual test cases for test_getValue.
#
#   Each test case has:
#   * A description, for debugging.
#   * A list of containers. Each container is a dictionary of the items that
#     will be set in that container. Note that this list is ordered in the order
#     of the stack. The first item should be referenced first.
#   * A key to search for.
#   * The expected result that should be returned when querying that key.
test_getValue_data = [
    {
        "description": "Empty stack",
        "containers": [
        ],
        "key": "foo",
        "result": None
    },
    {
        "description": "Nonexistent key",
        "containers": [
            { "boo": "bar" }
        ],
        "key": "foo",
        "result": None
    },
    {
        "description": "First hit",
        "containers": [
            { "foo": "bar" },
            { "foo": "baz" }
        ],
        "key": "foo",
        "result": "bar"
    },
    {
        "description": "Third hit",
        "containers": [
            { "boo": "baz" },
            { "zoo": "bam" },
            { "foo": "bar" }
        ],
        "key": "foo",
        "result": "bar"
    }
]

##  Tests getting item values from the container stack.
#
#   \param container_stack A new container stack from a fixture.
#   \param data Individual test cases as loaded from test_getValue_data.
@pytest.mark.parametrize("data", test_getValue_data)
def test_getValue(container_stack, data):
    # Fill the container stack with the containers.
    for container in reversed(data["containers"]): # Reverse order to make sure the last-added item is the top of the list.
        mockup = MockContainer()
        mockup.items = container
        container_stack.addContainer(mockup)

    answer = container_stack.getProperty(data["key"], "value") # Do the actual query.

    assert answer == data["result"]

##  Tests removing containers from the stack.
#
#   \param container_stack A new container stack from a fixture.
def test_removeContainer(container_stack):
    # First test the empty case.
    with pytest.raises(IndexError):
        container_stack.removeContainer(0)

    # Now add data.
    container0 = MockContainer()
    container_stack.addContainer(container0)
    with pytest.raises(IndexError):
        container_stack.removeContainer(1)
    with pytest.raises(IndexError):
        container_stack.removeContainer(-1)
    with pytest.raises(TypeError): # Curveball!
        container_stack.removeContainer("test")
    container_stack.removeContainer(0)
    assert container_stack.getContainers() == []

    # Multiple subcontainers.
    container0 = MockContainer()
    container1 = MockContainer()
    container2 = MockContainer()
    container_stack.addContainer(container0)
    container_stack.addContainer(container1)
    container_stack.addContainer(container2)
    container_stack.removeContainer(1)
    assert container_stack.getContainers() == [container2, container0]

##  Tests replacing a container in the stack.
#
#   \param container_stack A new container stack from a fixture.
def test_replaceContainer(container_stack):
    # First test the empty case.
    with pytest.raises(IndexError):
        container_stack.replaceContainer(0, MockContainer())

    # Now add data.
    container0 = MockContainer()
    container_stack.addContainer(container0)
    container0_replacement = MockContainer()
    with pytest.raises(IndexError):
        container_stack.replaceContainer(1, container0_replacement)
    with pytest.raises(IndexError):
        container_stack.replaceContainer(-1, container0_replacement)
    container_stack.replaceContainer(0, container0_replacement)
    assert container_stack.getContainers() == [container0_replacement]

    # Add multiple containers.
    container1 = MockContainer()
    container_stack.addContainer(container1)
    container2 = MockContainer()
    container_stack.addContainer(container2)
    container1_replacement = MockContainer()
    container_stack.replaceContainer(1, container1_replacement)
    assert container_stack.getContainers() == [container2, container1_replacement, container0_replacement]

    # Try to replace a container with itself.
    with pytest.raises(Exception):
        container_stack.replaceContainer(2, container_stack)
    assert container_stack.getContainers() == [container2, container1_replacement, container0_replacement]

##  Tests serialising and deserialising the container stack.
#
#   \param container_stack A new container stack from a fixture.
def test_serialize(container_stack):
    registry = UM.Settings.ContainerRegistry.getInstance() # All containers need to be registered in order to be recovered again after deserialising.

    # First test the empty container stack.
    _test_serialize_cycle(container_stack)

    # Case with one subcontainer.
    container = UM.Settings.InstanceContainer(uuid.uuid4().int)
    registry.addContainer(container)
    container_stack.addContainer(container)
    _test_serialize_cycle(container_stack)

    # Case with two subcontainers.
    container = UM.Settings.InstanceContainer(uuid.uuid4().int)
    registry.addContainer(container)
    container_stack.addContainer(container) # Already had one, if all previous assertions were correct.
    _test_serialize_cycle(container_stack)

    # Case with all types of subcontainers.
    container = UM.Settings.DefinitionContainer(uuid.uuid4().int)
    registry.addContainer(container)
    container_stack.addContainer(container)
    container = UM.Settings.ContainerStack(uuid.uuid4().int)
    registry.addContainer(container)
    container_stack.addContainer(container)
    _test_serialize_cycle(container_stack)

    # With some metadata.
    container_stack.getMetaData()["foo"] = "bar"
    _test_serialize_cycle(container_stack)

    # With a changed name.
    container_stack.setName("Fred")
    _test_serialize_cycle(container_stack)

    # A name with special characters, to test the encoding.
    container_stack.setName("ルベン")
    _test_serialize_cycle(container_stack)

    # Just to bully the one who implements this, a name with special characters in JSON and CFG.
    container_stack.setName("=,\"")
    _test_serialize_cycle(container_stack)

    # A container that is not in the registry.
    container_stack.addContainer(UM.Settings.DefinitionContainer(uuid.uuid4().int))
    serialised = container_stack.serialize()
    container_stack = UM.Settings.ContainerStack(uuid.uuid4().int) # Completely fresh container stack.
    with pytest.raises(Exception):
        container_stack.deserialize(serialised)

##  Tests whether changing the name of the stack has the proper effects.
#
#   \param container_stack A new container stack from a fixture.
#   \param application An application containing the thread handle for signals.
#   Must be included for the signal to check against the main thread in
#   auto-mode.
def test_setName(container_stack, application):
    name_change_counter = 0
    def increment_name_change_counter():
        nonlocal name_change_counter
        name_change_counter += 1
    container_stack.nameChanged.connect(increment_name_change_counter) # To make sure it emits the signal.

    different_name = "test"
    if container_stack.getName() == different_name:
        different_name = "tast" #Make sure it is actually different!
    container_stack.setName(different_name)
    assert container_stack.getName() == different_name # Name is correct.
    assert name_change_counter == 1 # Correctly signalled once.

    different_name += "_new" # Make it different again.
    container_stack.setName(different_name)
    assert container_stack.getName() == different_name # Name is updated again.
    assert name_change_counter == 2 # Correctly signalled once again.

    container_stack.setName(different_name) # Not different this time.
    assert container_stack.getName() == different_name
    assert name_change_counter == 2 # Didn't signal.

##  Tests the next stack functionality.
#
#   \param container_stack A new container stack from a fixture.
def test_setNextStack(container_stack):
    container = MockContainer()
    container_stack.setNextStack(container)
    assert container_stack.getNextStack() == container

    with pytest.raises(Exception):
        container_stack.setNextStack(container_stack) # Can't set itself as next stack.

##  Tests a single cycle of serialising and deserialising a container stack.
#
#   This will serialise and then deserialise the container stack, and sees if
#   the deserialised container stack is the same as the original one.
#
#   \param container_stack The container stack to serialise and deserialise.
def _test_serialize_cycle(container_stack):
    name = container_stack.getName()
    metadata = container_stack.getMetaData()
    containers = container_stack.getContainers()

    serialised = container_stack.serialize()
    container_stack = UM.Settings.ContainerStack(uuid.uuid4().int) # Completely fresh container stack.
    container_stack.deserialize(serialised)

    #ID and nextStack are allowed to be different.
    assert name == container_stack.getName()
    assert metadata == container_stack.getMetaData()
    assert containers == container_stack.getContainers()
