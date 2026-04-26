using System;
using System.IO;
using System.Windows;
using System.Windows.Input;
using System.Windows.Threading;
using Microsoft.Win32;

namespace WpfAudioPlayer;

public partial class MainWindow : Window
{
    private readonly DispatcherTimer _timer;
    private bool _isDraggingSlider;
    private bool _isMediaLoaded;
    private bool _isPlaying;

    public MainWindow()
    {
        InitializeComponent();

        _timer = new DispatcherTimer
        {
            Interval = TimeSpan.FromMilliseconds(250)
        };
        _timer.Tick += Timer_Tick;
    }

    private void OpenButton_Click(object sender, RoutedEventArgs e)
    {
        var dialog = new OpenFileDialog
        {
            Title = "Selecteer een audio bestand",
            Filter = "Audio bestanden (*.mp3;*.wav)|*.mp3;*.wav|MP3 (*.mp3)|*.mp3|WAV (*.wav)|*.wav|Alle bestanden (*.*)|*.*"
        };

        if (dialog.ShowDialog() == true)
        {
            LoadFile(dialog.FileName);
        }
    }

    private void LoadFile(string path)
    {
        try
        {
            MediaPlayer.Stop();
            _isPlaying = false;
            _isMediaLoaded = false;
            _timer.Stop();

            MediaPlayer.Source = new Uri(path, UriKind.Absolute);
            FileNameText.Text = Path.GetFileName(path);
            StatusText.Text = $"Laden: {path}";

            PlayButton.IsEnabled = true;
            PauseButton.IsEnabled = false;
            StopButton.IsEnabled = false;
        }
        catch (Exception ex)
        {
            StatusText.Text = $"Fout bij laden: {ex.Message}";
            MessageBox.Show(ex.Message, "Kan bestand niet laden", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    private void PlayButton_Click(object sender, RoutedEventArgs e)
    {
        MediaPlayer.Play();
        _isPlaying = true;
        _timer.Start();
        StatusText.Text = "Afspelen...";
        PlayButton.IsEnabled = false;
        PauseButton.IsEnabled = true;
        StopButton.IsEnabled = true;
    }

    private void PauseButton_Click(object sender, RoutedEventArgs e)
    {
        MediaPlayer.Pause();
        _isPlaying = false;
        _timer.Stop();
        StatusText.Text = "Gepauzeerd";
        PlayButton.IsEnabled = true;
        PauseButton.IsEnabled = false;
        StopButton.IsEnabled = true;
    }

    private void StopButton_Click(object sender, RoutedEventArgs e)
    {
        MediaPlayer.Stop();
        _isPlaying = false;
        _timer.Stop();
        PositionSlider.Value = 0;
        CurrentTimeText.Text = "00:00";
        StatusText.Text = "Gestopt";
        PlayButton.IsEnabled = _isMediaLoaded;
        PauseButton.IsEnabled = false;
        StopButton.IsEnabled = false;
    }

    private void VolumeSlider_ValueChanged(object sender, RoutedPropertyChangedEventArgs<double> e)
    {
        if (MediaPlayer != null)
        {
            MediaPlayer.Volume = e.NewValue;
        }
        if (VolumeText != null)
        {
            VolumeText.Text = $"{(int)Math.Round(e.NewValue * 100)}%";
        }
    }

    private void MediaPlayer_MediaOpened(object sender, RoutedEventArgs e)
    {
        _isMediaLoaded = true;
        if (MediaPlayer.NaturalDuration.HasTimeSpan)
        {
            var total = MediaPlayer.NaturalDuration.TimeSpan;
            PositionSlider.Maximum = total.TotalSeconds;
            TotalTimeText.Text = FormatTime(total);
        }
        else
        {
            PositionSlider.Maximum = 1;
            TotalTimeText.Text = "00:00";
        }
        StatusText.Text = "Klaar om af te spelen";
    }

    private void MediaPlayer_MediaEnded(object sender, RoutedEventArgs e)
    {
        MediaPlayer.Stop();
        _isPlaying = false;
        _timer.Stop();
        PositionSlider.Value = 0;
        CurrentTimeText.Text = "00:00";
        StatusText.Text = "Einde bereikt";
        PlayButton.IsEnabled = true;
        PauseButton.IsEnabled = false;
        StopButton.IsEnabled = false;
    }

    private void MediaPlayer_MediaFailed(object sender, ExceptionRoutedEventArgs e)
    {
        _isMediaLoaded = false;
        _isPlaying = false;
        _timer.Stop();
        StatusText.Text = $"Afspeelfout: {e.ErrorException.Message}";
        MessageBox.Show(e.ErrorException.Message, "Afspeelfout", MessageBoxButton.OK, MessageBoxImage.Error);
        PlayButton.IsEnabled = false;
        PauseButton.IsEnabled = false;
        StopButton.IsEnabled = false;
    }

    private void Timer_Tick(object? sender, EventArgs e)
    {
        if (_isDraggingSlider) return;
        if (!MediaPlayer.NaturalDuration.HasTimeSpan) return;

        var current = MediaPlayer.Position;
        PositionSlider.Value = current.TotalSeconds;
        CurrentTimeText.Text = FormatTime(current);
    }

    private void PositionSlider_DragStarted(object sender, System.Windows.Controls.Primitives.DragStartedEventArgs e)
    {
        _isDraggingSlider = true;
    }

    private void PositionSlider_DragCompleted(object sender, System.Windows.Controls.Primitives.DragCompletedEventArgs e)
    {
        _isDraggingSlider = false;
        SeekToSliderPosition();
    }

    private void PositionSlider_PreviewMouseUp(object sender, MouseButtonEventArgs e)
    {
        SeekToSliderPosition();
    }

    private void SeekToSliderPosition()
    {
        if (!_isMediaLoaded) return;
        var seconds = PositionSlider.Value;
        MediaPlayer.Position = TimeSpan.FromSeconds(seconds);
        CurrentTimeText.Text = FormatTime(MediaPlayer.Position);
    }

    private static string FormatTime(TimeSpan ts)
    {
        return ts.TotalHours >= 1
            ? ts.ToString(@"hh\:mm\:ss")
            : ts.ToString(@"mm\:ss");
    }
}
