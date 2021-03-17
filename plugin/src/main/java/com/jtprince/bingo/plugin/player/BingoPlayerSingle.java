package com.jtprince.bingo.plugin.player;

import com.jtprince.bingo.plugin.MCBingoPlugin;
import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.TextComponent;
import org.bukkit.Bukkit;
import org.bukkit.OfflinePlayer;
import org.bukkit.entity.Player;
import org.jetbrains.annotations.NotNull;

import java.util.Collection;
import java.util.Collections;
import java.util.UUID;

public class BingoPlayerSingle extends BingoPlayer {
    private final UUID playerUuid;

    public BingoPlayerSingle(OfflinePlayer player) {
        this.playerUuid = player.getUniqueId();
    }

    @Override
    public @NotNull String getName() {
        String playerName = Bukkit.getOfflinePlayer(playerUuid).getName();
        if (playerName == null) {
            MCBingoPlugin.logger().warning("getName for player " + playerUuid + " is null");
            return playerUuid.toString();
        }

        return playerName;
    }

    @Override
    public @NotNull TextComponent getFormattedName() {
        return Component.text(this.getName());
    }

    @Override
    public @NotNull Collection<Player> getBukkitPlayers() {
        Player bukkitPlayer = Bukkit.getPlayer(playerUuid);
        if (bukkitPlayer == null || !bukkitPlayer.isOnline()) {
            return Collections.emptySet();
        }

        return Collections.singleton(bukkitPlayer);
    }
}
