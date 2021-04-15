package com.jtprince.bingo.kplugin.player

import net.kyori.adventure.text.Component
import org.bukkit.entity.Player

abstract class BingoPlayer {
    /**
     * The name that should be used on the WebSocket, and will be displayed on the webpage.
     */
    abstract val name: String

    /**
     * The name that should be used on the WebSocket, but formatted nicely.
     */
    abstract val formattedName: Component

    /**
     * A list of {@link org.bukkit.entity.Player}s that are online playing as this BingoPlayer.
     * If no Bukkit Players playing as this BingoPlayer are online, returns an empty collection.
     */
    abstract val bukkitPlayers: Collection<Player>

    /**
     * The Player's name with Spaces stripped out.
     */
    val slugName: String
        get() = name.replace(" ", "")
}