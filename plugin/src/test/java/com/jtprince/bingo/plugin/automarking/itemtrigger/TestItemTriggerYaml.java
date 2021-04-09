package com.jtprince.bingo.plugin.automarking.itemtrigger;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;
import static org.junit.jupiter.api.Assertions.assertEquals;

/**
 * Test the functionality of the Item Trigger YAML parser.
 */
public class TestItemTriggerYaml {
    final static String YAML_PATH = "/test_item_triggers.yml";
    final ItemTriggerYaml yaml;

    public TestItemTriggerYaml() {
        yaml = ItemTriggerYaml.fromFile(getClass().getResourceAsStream(YAML_PATH));
    }

    @Test
    void testYamlBasic() {
        ItemTriggerYaml.MatchGroup g = yaml.get("jm_book_quill");
        assertNotNull(g);
        assertTrue(g.nameMatches("minecraft:writable_book"));
        assertFalse(g.nameMatches("minecraft:book"));
        assertEquals(1, g.unique);
        assertEquals(1, g.total);
        assertEquals(0, g.children.size());
    }

    @Test
    void testYamlNonexistent() {
        ItemTriggerYaml.MatchGroup g = yaml.get("nonexistent_goal_id");
        assertNull(g);
    }

    @Test
    void testYamlGroups() {
        ItemTriggerYaml.MatchGroup g = yaml.get("jm_different_edible");
        assertNotNull(g);
        assertTrue(g.nameMatches("minecraft:beetroot"));
        assertTrue(g.nameMatches("minecraft:regex_stew"));
        assertFalse(g.nameMatches("minecraft:potato"));  // In child
        assertEquals(6, g.unique);
        assertEquals(2, g.children.size());

        ItemTriggerYaml.MatchGroup potatoChild = g.children.get(0);
        assertNotNull(potatoChild);
        assertTrue(potatoChild.nameMatches("minecraft:potato"));
        assertFalse(potatoChild.nameMatches("minecraft:beetroot"));
        assertEquals(1, potatoChild.unique);
        assertEquals(1, potatoChild.total);
        assertEquals(0, potatoChild.children.size());
    }
}