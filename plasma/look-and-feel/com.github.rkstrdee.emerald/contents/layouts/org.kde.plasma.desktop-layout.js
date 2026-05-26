var panel = new Panel;
panel.location = "bottom";
panel.hiding = "normal";
panel.height = 2 * Math.floor(gridUnit * 1.8 / 2);
panel.lengthMode = "manual";
panel.alignment = "center";
panel.maximumLength = 85.375 * gridUnit;
panel.minimumLength = 85.375 * gridUnit;
panel.offset = 0;

var launcher = panel.addWidget("org.kde.plasma.kickoff");
launcher.currentConfigGroup = ["Shortcuts"];
launcher.writeConfig("global", "Alt+F1");
launcher.currentConfigGroup = ["/Configuration/General"];
launcher.writeConfig("favoritesPortedToKAstats", true);
launcher.writeConfig("icon", "start-here-kde");

panel.addWidget("org.kde.plasma.panelspacer");
panel.addWidget("org.kde.plasma.icontasks");
panel.addWidget("org.kde.plasma.panelspacer");
panel.addWidget("org.kde.plasma.systemtray");

var clock = panel.addWidget("org.kde.plasma.digitalclock");
clock.currentConfigGroup = ["/"];
clock.writeConfig("showDate", false);

var desktopArray = desktopsForActivity(currentActivity());
for (var desktopIndex = 0; desktopIndex < desktopArray.length; desktopIndex++) {
    desktopArray[desktopIndex].wallpaperPlugin = "org.kde.image";
    desktopArray[desktopIndex].currentConfigGroup = ["/Wallpaper/org.kde.image/General"];
    desktopArray[desktopIndex].writeConfig("Image", "file:///usr/share/wallpapers/cachyos-wallpapers/CachyOS_GreenSpace.png");
}
