#include <gtest/gtest.h>
#include "ParseRaiData.h"
#include <QString>

class ParseRaiDataTest : public ::testing::Test
{
protected:
    void SetUp() override {}
    void TearDown() override {}
};

// Test parsing a valid complete HRI message with all fields
TEST_F(ParseRaiDataTest, ParseValidCompleteMessage)
{
    QString jsonStr = R"({
        "type": "tool_call",
        "tool_name": "move_object",
        "tool_call": "execute_move",
        "tool_args": {
            "object_id": "box_123",
            "target_x": "1.5",
            "target_y": "2.0"
        }
    })";

    auto result = ParseRaiData::parseHRIMessage(jsonStr);

    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(result->type_, QString("tool_call"));
    EXPECT_EQ(result->tool_name_, QString("move_object"));
    EXPECT_EQ(result->tool_call_, QString("execute_move"));
    EXPECT_EQ(result->parameters_.size(), 3);
    EXPECT_EQ(result->parameters_["object_id"], QString("box_123"));
    EXPECT_EQ(result->parameters_["target_x"], QString("1.5"));
    EXPECT_EQ(result->parameters_["target_y"], QString("2.0"));
}

// Test parsing a message with minimal fields (only type)
TEST_F(ParseRaiDataTest, ParseMinimalMessage)
{
    QString jsonStr = R"({
        "type": "status_update",
        "tool_args": {}
    })";

    auto result = ParseRaiData::parseHRIMessage(jsonStr);

    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(result->type_, QString("status_update"));
    EXPECT_TRUE(result->tool_name_.isEmpty());
    EXPECT_TRUE(result->tool_call_.isEmpty());
    EXPECT_TRUE(result->parameters_.isEmpty());
}

// Test parsing a message with only tool_name
TEST_F(ParseRaiDataTest, ParseMessageWithToolNameOnly)
{
    QString jsonStr = R"({
        "tool_name": "move_object_from_pose_to_inspection_area",
        "tool_args": {}
    })";

    auto result = ParseRaiData::parseHRIMessage(jsonStr);

    ASSERT_TRUE(result.has_value());
    EXPECT_TRUE(result->type_.isEmpty());
    EXPECT_EQ(result->tool_name_, QString("move_object_from_pose_to_inspection_area"));
    EXPECT_TRUE(result->tool_call_.isEmpty());
    EXPECT_TRUE(result->parameters_.isEmpty());
}

// Test parsing a message with empty tool_args
TEST_F(ParseRaiDataTest, ParseMessageWithEmptyToolArgs)
{
    QString jsonStr = R"({
        "type": "command",
        "tool_name": "reset",
        "tool_call": "system_reset",
        "tool_args": {}
    })";

    auto result = ParseRaiData::parseHRIMessage(jsonStr);

    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(result->type_, QString("command"));
    EXPECT_EQ(result->tool_name_, QString("reset"));
    EXPECT_EQ(result->tool_call_, QString("system_reset"));
    EXPECT_TRUE(result->parameters_.isEmpty());
}

// Test parsing a message with multiple tool_args
TEST_F(ParseRaiDataTest, ParseMessageWithMultipleToolArgs)
{
    QString jsonStr = R"({
        "type": "navigation",
        "tool_name": "navigate_to_point",
        "tool_call": "nav_execute",
        "tool_args": {
            "x": "10.5",
            "y": "20.3",
            "z": "0.0",
            "frame": "map",
            "speed": "0.5"
        }
    })";

    auto result = ParseRaiData::parseHRIMessage(jsonStr);

    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(result->parameters_.size(), 5);
    EXPECT_EQ(result->parameters_["x"], QString("10.5"));
    EXPECT_EQ(result->parameters_["y"], QString("20.3"));
    EXPECT_EQ(result->parameters_["z"], QString("0.0"));
    EXPECT_EQ(result->parameters_["frame"], QString("map"));
    EXPECT_EQ(result->parameters_["speed"], QString("0.5"));
}

// Test parsing invalid JSON (not an object)
TEST_F(ParseRaiDataTest, ParseInvalidJSONArray)
{
    QString jsonStr = R"(["type", "tool_call"])";

    auto result = ParseRaiData::parseHRIMessage(jsonStr);

    EXPECT_FALSE(result.has_value());
}

// Test parsing invalid JSON (malformed)
TEST_F(ParseRaiDataTest, ParseMalformedJSON)
{
    QString jsonStr = R"({type: "tool_call", invalid json})";

    auto result = ParseRaiData::parseHRIMessage(jsonStr);

    EXPECT_FALSE(result.has_value());
}

// Test parsing empty string
TEST_F(ParseRaiDataTest, ParseEmptyString)
{
    QString jsonStr = "";

    auto result = ParseRaiData::parseHRIMessage(jsonStr);

    EXPECT_FALSE(result.has_value());
}

// Test parsing null JSON
TEST_F(ParseRaiDataTest, ParseNullJSON)
{
    QString jsonStr = "null";

    auto result = ParseRaiData::parseHRIMessage(jsonStr);

    EXPECT_FALSE(result.has_value());
}

// Test parsing JSON with non-string type field
TEST_F(ParseRaiDataTest, ParseMessageWithNonStringType)
{
    QString jsonStr = R"({
        "type": 123,
        "tool_name": "test",
        "tool_args": {}
    })";

    auto result = ParseRaiData::parseHRIMessage(jsonStr);

    ASSERT_TRUE(result.has_value());
    EXPECT_TRUE(result->type_.isEmpty()); // Should be empty since type is not a string
    EXPECT_EQ(result->tool_name_, QString("test"));
}

// Test parsing JSON with non-string tool_name field
TEST_F(ParseRaiDataTest, ParseMessageWithNonStringToolName)
{
    QString jsonStr = R"({
        "type": "command",
        "tool_name": 456,
        "tool_args": {}
    })";

    auto result = ParseRaiData::parseHRIMessage(jsonStr);

    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(result->type_, QString("command"));
    EXPECT_TRUE(result->tool_name_.isEmpty()); // Should be empty since tool_name is not a string
}

// Test parsing JSON with non-string values in tool_args (should be ignored)
TEST_F(ParseRaiDataTest, ParseMessageWithNonStringToolArgs)
{
    QString jsonStr = R"({
        "type": "command",
        "tool_name": "test",
        "tool_call": "execute",
        "tool_args": {
            "valid_param": "string_value",
            "invalid_number": 123,
            "invalid_bool": true,
            "invalid_object": {"nested": "value"}
        }
    })";

    auto result = ParseRaiData::parseHRIMessage(jsonStr);

    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(result->parameters_.size(), 1); // Only valid_param should be included
    EXPECT_EQ(result->parameters_["valid_param"], QString("string_value"));
    EXPECT_FALSE(result->parameters_.contains("invalid_number"));
    EXPECT_FALSE(result->parameters_.contains("invalid_bool"));
    EXPECT_FALSE(result->parameters_.contains("invalid_object"));
}

// Test parsing JSON with missing tool_args field
TEST_F(ParseRaiDataTest, ParseMessageWithMissingToolArgs)
{
    QString jsonStr = R"({
        "type": "status",
        "tool_name": "check_status"
    })";

    auto result = ParseRaiData::parseHRIMessage(jsonStr);

    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(result->type_, QString("status"));
    EXPECT_EQ(result->tool_name_, QString("check_status"));
    EXPECT_TRUE(result->parameters_.isEmpty());
}

// Test parsing JSON with Unicode characters
TEST_F(ParseRaiDataTest, ParseMessageWithUnicodeCharacters)
{
    QString jsonStr = R"({
        "type": "message",
        "tool_name": "display_text",
        "tool_call": "show",
        "tool_args": {
            "text": "Hello 世界 🌍",
            "language": "mixed"
        }
    })";

    auto result = ParseRaiData::parseHRIMessage(jsonStr);

    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(result->type_, QString("message"));
    EXPECT_EQ(result->parameters_["text"], QString("Hello 世界 🌍"));
    EXPECT_EQ(result->parameters_["language"], QString("mixed"));
}

// Test parsing JSON with empty string values
TEST_F(ParseRaiDataTest, ParseMessageWithEmptyStringValues)
{
    QString jsonStr = R"({
        "type": "",
        "tool_name": "",
        "tool_call": "",
        "tool_args": {
            "param1": "",
            "param2": "value"
        }
    })";

    auto result = ParseRaiData::parseHRIMessage(jsonStr);

    ASSERT_TRUE(result.has_value());
    EXPECT_TRUE(result->type_.isEmpty());
    EXPECT_TRUE(result->tool_name_.isEmpty());
    EXPECT_TRUE(result->tool_call_.isEmpty());
    EXPECT_EQ(result->parameters_.size(), 2);
    EXPECT_TRUE(result->parameters_["param1"].isEmpty());
    EXPECT_EQ(result->parameters_["param2"], QString("value"));
}

// Test parsing JSON with special characters
TEST_F(ParseRaiDataTest, ParseMessageWithSpecialCharacters)
{
    QString jsonStr = R"({
        "type": "test",
        "tool_name": "special_chars",
        "tool_call": "execute",
        "tool_args": {
            "path": "C:\\Users\\test\\file.txt",
            "quote": "He said \"hello\"",
            "newline": "line1\nline2"
        }
    })";

    auto result = ParseRaiData::parseHRIMessage(jsonStr);

    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(result->parameters_["path"], QString("C:\\Users\\test\\file.txt"));
    EXPECT_EQ(result->parameters_["quote"], QString("He said \"hello\""));
    EXPECT_EQ(result->parameters_["newline"], QString("line1\nline2"));
}

// Test parsing real-world example from the comment in header
TEST_F(ParseRaiDataTest, ParseRealWorldExample)
{
    QString jsonStr = R"({
        "type": "tool_call",
        "tool_name": "move_object_from_pose_to_inspection_area",
        "tool_call": "execute_movement",
        "tool_args": {
            "object_pose_x": "1.0",
            "object_pose_y": "2.0",
            "object_pose_z": "0.5"
        }
    })";

    auto result = ParseRaiData::parseHRIMessage(jsonStr);

    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(result->type_, QString("tool_call"));
    EXPECT_EQ(result->tool_name_, QString("move_object_from_pose_to_inspection_area"));
    EXPECT_EQ(result->tool_call_, QString("execute_movement"));
    EXPECT_EQ(result->parameters_.size(), 3);
}

int main(int argc, char **argv)
{
    testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}