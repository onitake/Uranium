# Copyright (c) 2016 Ultimaker B.V.
# Uranium is released under the terms of the AGPLv3 or higher.

import pytest
import os.path
import uuid

import UM.Settings
from UM.Settings.DefinitionContainer import IncorrectDefinitionVersionError, InvalidDefinitionError
from UM.Settings.SettingDefinition import SettingDefinition, DefinitionPropertyType
from UM.Resources import Resources

Resources.addSearchPath(os.path.dirname(os.path.abspath(__file__)))

##  A fixture to create new definition containers with.
#
#   The container will have a unique ID.
@pytest.fixture
def definition_container():
    uid = str(uuid.uuid4().int)
    result = UM.Settings.DefinitionContainer(uid)
    assert result.getId() == uid
    return result

test_deserialize_data = [
    ("basic.def.json", { "name": "Test", "metadata": {}, "settings": {} }),
    ("metadata.def.json", { "name": "Test", "metadata": { "author": "Ultimaker", "category": "Test" }, "settings": {} }),
    ("single_setting.def.json", { "name": "Test", "metadata": {}, "settings": { "test_setting": { "label": "Test", "default_value": 10, "description": "A Test Setting" } } }),
    ("multiple_settings.def.json", { "name": "Test", "metadata": {}, "settings": {
        "test_setting_0": { "label": "Test 0", "default_value": 10, "description": "A Test Setting" },
        "test_setting_1": { "label": "Test 1", "default_value": 10, "description": "A Test Setting" },
        "test_setting_2": { "label": "Test 2", "default_value": 10, "description": "A Test Setting" },
        "test_setting_3": { "label": "Test 3", "default_value": 10, "description": "A Test Setting" },
        "test_setting_4": { "label": "Test 4", "default_value": 10, "description": "A Test Setting" }
    }}),
    ("children.def.json", { "name": "Test", "metadata": {}, "settings": {
        "test_setting": { "label": "Test", "default_value": 10, "description": "A Test Setting"},
        "test_child_0": { "label": "Test Child 0", "default_value": 10, "description": "A Test Setting"},
        "test_child_1": { "label": "Test Child 1", "default_value": 10, "description": "A Test Setting"},
    }}),
    ("inherits.def.json", { "name": "Inherits", "metadata": {"author": "Ultimaker", "category": "Other", "manufacturer": "Ultimaker" }, "settings": {
        "test_setting": { "label": "Test", "default_value": 11, "description": "A Test Setting" },
        "test_setting_1": { "label": "Test 1", "default_value": 10, "description": "A Test Setting" },
    }}),
    ("functions.def.json", { "name": "Test", "metadata": {}, "settings": {
        "test_setting_0": { "label": "Test 0", "default_value": 10, "description": "A Test Setting" },
        "test_setting_1": { "label": "Test 1", "default_value": 10, "description": "A Test Setting", "value": UM.Settings.SettingFunction("test_setting_0 * 10") },
    }})
]
@pytest.mark.parametrize("file,expected", test_deserialize_data)
def test_deserialize(file, expected, definition_container):
    json = ""
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "definitions", file)) as data:
        json = data.read()

    definition_container.deserialize(json)

    assert definition_container.getName() == expected["name"]

    for key, value in expected["metadata"].items():
        assert definition_container.getMetaDataEntry(key) == value

    for key, value in expected["settings"].items():
        settings = definition_container.findDefinitions(key = key)

        assert len(settings) == 1

        setting = settings[0]
        assert setting.key == key

        for property, property_value in value.items():
            assert getattr(setting, property) == property_value

##  Tests deserialising bad definition container JSONs.
#
#   \param definition_container A definition container from a fixture.
def test_deserialize_bad(definition_container):
    json = """{""" # Syntax error: No closing bracket!
    with pytest.raises(Exception):
        definition_container.deserialize(json)

    json = """{
    "version":
}""" # Syntax error: Missing value.
    with pytest.raises(Exception):
        definition_container.deserialize(json)

    json = """{
    "version": 2,
    "name": "Test",
    "settings": {}
}""" # Missing metadata.
    with pytest.raises(InvalidDefinitionError):
        definition_container.deserialize(json)

    json = """{
    "version": 2,
    "name": "Test",
    "metadata": {}
}""" # Missing settings.
    with pytest.raises(InvalidDefinitionError):
        definition_container.deserialize(json)

    json = """{
    "version": 2,
    "metadata": {},
    "settings": {}
}""" # Missing name.
    with pytest.raises(InvalidDefinitionError):
        definition_container.deserialize(json)

    json = """{
    "name": "Test",
    "metadata": {},
    "settings": {}
}""" # Missing version.
    with pytest.raises(InvalidDefinitionError):
        definition_container.deserialize(json)

    json = """{
    "version": 1,
    "name": "Test",
    "metadata": {},
    "settings": {}
}""" # Wrong version.
    with pytest.raises(IncorrectDefinitionVersionError):
        definition_container.deserialize(json)

    json = """{
    "version": 2,
    "name": "Test",
    "metadata": {},
    "settings": {},
    "inherits": "non-existent_file"
}""" # Faulty inheritance.
    with pytest.raises(OSError):
        definition_container.deserialize(json)

    json = """{
    "version": 2,
    "name": "Test",
    "metadata": {},
    "settings": {
        "layer_height": {
            "label": "Testiness of your print.",
            "description": "How testy your print should be."
        }
    }
}""" # Type missing from a setting.
    with pytest.raises(AttributeError):
        definition_container.deserialize(json)

##  Individual test cases for test_findDefinitions.
#
#   Each test case is a tuple consisting of:
#   * A description for debugging.
#   * A query to filter the definitions by.
#   * The expected result of the query.
#   * The data to build a definition container. The data is a list of
#     dictionaries, each dictionary representing one SettingDefinition instance.
#     When a dictionary has a "children" element, the contents of that element
#     will be created as children of the SettingDefinition.
test_findDefinitions_data = [
    # Description        Query                      Expected result                                 Data
    ("Empty input",      { "key": "foo" },          [ ],                                            [ ]),
    ("Empty query",      { },                       [ { "key": "foo", "default_value": "bar" } ],   [ { "key": "foo", "default_value": "bar" } ]),
    ("Single hit",       { "key": "foo" },          [ { "key": "foo", "default_value": "bar" } ],   [ { "key": "foo", "default_value": "bar" } ]),
    ("Search child",     { "key": "child" },        [ { "key": "child", "default_value": "bah" } ], [ { "key": "foo", "default_value": "bar", "children": [ { "key": "child", "default_value": "bah" } ] } ]),
    ("Choice",           { "key": "zoo" },          [ { "key": "zoo", "default_value": "baz" } ],   [ { "key": "foo", "default_value": "bar" },
                                                                                                      { "key": "zoo", "default_value": "baz" } ]),
    ("Multiple answers", { "default_value": "bar"}, [ { "key": "foo", "default_value": "bar" },
                                                      { "key": "boo", "default_value": "bar" } ],   [ { "key": "foo", "default_value": "bar" }, { "key": "boo", "default_value": "bar" } ]),
    ("Multiple filters", { "key": "moo",
                           "default_value": "bar"}, [ { "key": "moo", "default_value": "bar" } ],   [ { "key": "foo", "default_value": "boo" },
                                                                                                      { "key": "moo", "default_value": "bar" },
                                                                                                      { "key": "zoo", "default_value": "bar" } ])
]

##  Tests the filtering of definitions.
#
#   \param description A description of the test case (unused).
#   \param query The query to filter by.
#   \param result The expected result of the query.
#   \param data The data to build a definition container.
@pytest.mark.parametrize("description,query,result,data", test_findDefinitions_data)
def test_findDefinitions(description, query, result, data, definition_container):
    # Construct the data in the definition container.
    for definition in data:
        definition_container.definitions.append(_createSettingDefinition(definition))

    answers = definition_container.findDefinitions(**query) # Perform the actual query.

    assert len(result) == len(answers)
    for expected in result: # Each expected result must be present in the answer.
        for answer in answers:
            for key, value in expected.items():
                if getattr(answer, key) != value:
                    break
            else: # Match!
                break
        else: # No match!
            assert False
    # All expected answers had a match, so it's a good answer.

##  Tests getting metadata entries.
#
#   \param definition_container A new definition container from a fixture.
def test_getMetaDataEntry(definition_container):
    metadata = definition_container.getMetaData()

    metadata["foo"] = "bar" # Normal case.
    assert definition_container.getMetaDataEntry("foo") == "bar"

    assert definition_container.getMetaDataEntry("zoo", 42) == 42 # Non-existent entry must return the default.

##  The individual test cases for test_getValue.
#
#   The first entry is a description for debugging.
#
#   The second entry is a key to search for in the definitions.
#
#   The third entry is the value that is expected to be returned.
#
#   The fourth entry is the data structure that is constructed to search in. The
#   data is a list of dictionaries, each dictionary representing one
#   SettingDefinition instance. When a dictionary has a "children" element, the
#   contents of that element will be created as children of the
#   SettingDefinition.
test_getValue_data = [
    # Description     Key    Value  Data
    ("Simple get",    "foo", "bar",   [ { "key": "foo", "default_value": "bar" } ]),
    ("Missing entry", "zoo", None,    [ { "key": "foo", "default_value": "bar" } ]),
    ("Get int",       "who", 42,      [ { "key": "foo", "default_value": "bar" }, { "key": "who", "default_value": 42 } ]),
    ("Subsetting",    "child", "bar", [ { "key": "boo", "default_value": "zar" }, { "key": "parent", "default_value": 1, "children": [ { "key": "child", "default_value": "bar" } ] } ]),
    ("Subsubsetting", "foo", "bar",   [ { "key": "boo", "default_value": "zar" }, { "key": "parent", "default_value": 1, "children": [ { "key": "child", "default_value": 2, "children": [ { "key": "foo", "default_value": "bar" } ] } ] } ]),
    ("Two options",   "foo", "bar",   [ { "key": "foo", "default_value": "bar" }, { "key": "foo", "default_value": "bar" } ])
]

##  Tests the getting of default values in the definition container.
#
#   \param description A description for the test case.
#   \param key The key to search for in the definitions.
#   \param value The value that is expected to be returned.
#   \param data The data structure that is constructed to search in.
#   \param definition_container A new definition container from a fixture.
@pytest.mark.parametrize("description,key,value,data", test_getValue_data)
def test_getValue(description, key, value, data, definition_container):
    # First build the data structure in the definition container.
    for item in data:
        definition_container.definitions.append(_createSettingDefinition(item))

    # Now perform the request that we're testing.
    answer = definition_container.getProperty(key, "value")

    assert answer == value

##  Tests the serialisation and deserialisation process.
#
#   \param definition_container A new definition container from a fixture.
def test_serialize(definition_container):
    # First test with an empty container.
    _test_serialize_cycle(definition_container)

    # Change the name.
    definition_container._name = "Bla!"
    _test_serialize_cycle(definition_container)
    definition_container._name = "[\"\n{':" # Some characters that might need to be escaped.
    _test_serialize_cycle(definition_container)
    definition_container._name = "ルベン" # From a different character set (UTF-8 test).
    _test_serialize_cycle(definition_container)

    # Add some metadata.
    definition_container.getMetaData()["author"] = "Testy McTesticle"
    definition_container.getMetaData()["escape_test"] = "[\"\n{':"
    _test_serialize_cycle(definition_container)

    # Add some subsettings.
    subsetting = _createSettingDefinition({
        "key": "parent",
        "default_value": "newspaper",
        "children": [
            {
                "key": "child",
                "default_value": "tv",
                "children": [
                    {
                        "key": "grandchild",
                        "default_value": "Nintendo"
                    }
                ]
            }
        ]
    })
    definition_container.definitions.append(subsetting)
    _test_serialize_cycle(definition_container)

def test_setting_function():
    container = UM.Settings.DefinitionContainer("test")
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "definitions", "functions.def.json")) as data:
        container.deserialize(data.read())

    setting_0 = container.findDefinitions(key = "test_setting_0")[0]
    setting_1 = container.findDefinitions(key = "test_setting_1")[0]

    function = setting_1.value

    assert len(setting_0.relations) == 1
    assert len(setting_1.relations) == 1

    relation_0 = setting_0.relations[0]
    relation_1 = setting_1.relations[0]

    assert relation_0.owner == setting_0
    assert relation_0.target == setting_1
    assert relation_0.type == UM.Settings.SettingRelation.RelationType.RequiredByTarget
    assert relation_0.role == "value"

    assert relation_1.owner == setting_1
    assert relation_1.target == setting_0
    assert relation_1.type == UM.Settings.SettingRelation.RelationType.RequiresTarget
    assert relation_1.role == "value"

    assert isinstance(function, UM.Settings.SettingFunction)

    result = function(container)
    assert result == (setting_0.default_value * 10)

##  Creates a setting definition from a dictionary of properties.
#
#   The key must be present in the properties. It will be the key of the setting
#   definition. The default value and children will be added if they are present
#   in the dictionary.
#
#   \param properties A dictionary of properties for the setting definition.
#   Only the key, default value and children are used.
def _createSettingDefinition(properties):
    result = SettingDefinition(properties["key"]) # Key MUST be present.
    if "default_value" in properties:
        result._SettingDefinition__property_values["default_value"] = properties["default_value"] # Nota bene: Setting a private value depends on implementation, but changing a property is not currently exposed.
    result._SettingDefinition__property_values["description"] = "Test setting definition"
    result._SettingDefinition__property_values["type"] = "str"
    if "children" in properties:
        for child in properties["children"]:
            result.children.append(_createSettingDefinition(child))
    return result

##  Tests one cycle of serialising and deserialising.
#
#   This makes a copy of all properties of the definition container, then
#   serialises the container to a string and deserialises it again from that
#   string. Then it verifies that all properties are still the same.
#
#   \param definition_container A defintion container to test the serialisation
#   of.
def _test_serialize_cycle(definition_container):
    # Don't verify the ID. It must be unique, so it must be different.
    name = definition_container.getName()
    metadata = definition_container.getMetaData()
    definitions = definition_container.definitions
    # No need to verify the internationalisation catalogue.

    serialised = definition_container.serialize()
    deserialised = UM.Settings.DefinitionContainer(uuid.uuid4().int)
    deserialised.deserialize(serialised)

    assert name == deserialised.getName()
    assert metadata == deserialised.getMetaData()
    assert definitions == deserialised.definitions
