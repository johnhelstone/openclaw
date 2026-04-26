# WPF Audio Player

Een eenvoudige WPF (.NET 8.0) Windows-applicatie waarmee je `.wav` en `.mp3` bestanden kunt afspelen.

## Functies

- Bestand openen (`.mp3` / `.wav`)
- Afspelen / Pauze / Stop
- Voortgangsbalk met scrubben (klik of sleep)
- Volume slider
- Tijdsweergave (huidig / totaal)
- Donker thema

## Vereisten

- Windows 10 of 11 (x64)
- [.NET 8 SDK](https://dotnet.microsoft.com/download/dotnet/8.0) (alleen nodig voor het builden)

## Snel starten (publish naar `.exe`)

1. Pak deze map uit op een Windows-machine.
2. Dubbelklik op **`nuuk-batch-run-publish.bat`**.
3. Wacht tot het script klaar is. De gepubliceerde `.exe` staat in:
   ```
   publish\WpfAudioPlayer.exe
   ```
4. Druk op een toets om de app te starten, of voer de `.exe` later handmatig uit.

De build is een **self-contained, single-file** executable voor `win-x64`. De
gebruiker hoeft .NET _niet_ apart te installeren om de `.exe` uit te voeren.

## Vanuit Visual Studio / Rider

Open `WpfAudioPlayer.csproj` en druk op Run (F5).

## Vanuit de command line (zonder publish)

```cmd
dotnet run --project WpfAudioPlayer.csproj
```

## Projectstructuur

```
WpfAudioPlayer/
├── App.xaml
├── App.xaml.cs
├── MainWindow.xaml
├── MainWindow.xaml.cs
├── WpfAudioPlayer.csproj
├── nuuk-batch-run-publish.bat
└── README.md
```
