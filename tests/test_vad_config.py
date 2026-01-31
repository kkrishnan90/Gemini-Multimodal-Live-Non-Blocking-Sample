"""Tests for VAD (Voice Activity Detection) configuration."""
import pytest
from google.genai import types


def test_vad_enums_exist():
    """Test that all required VAD enums exist in the SDK."""
    # StartSensitivity
    assert hasattr(types, 'StartSensitivity')
    assert hasattr(types.StartSensitivity, 'START_SENSITIVITY_HIGH')
    assert hasattr(types.StartSensitivity, 'START_SENSITIVITY_LOW')

    # EndSensitivity
    assert hasattr(types, 'EndSensitivity')
    assert hasattr(types.EndSensitivity, 'END_SENSITIVITY_HIGH')
    assert hasattr(types.EndSensitivity, 'END_SENSITIVITY_LOW')

    # ActivityHandling (for barge-in/interruption)
    assert hasattr(types, 'ActivityHandling')
    assert hasattr(types.ActivityHandling, 'START_OF_ACTIVITY_INTERRUPTS')
    assert hasattr(types.ActivityHandling, 'NO_INTERRUPTION')


def test_realtime_input_config_creation():
    """Test creating RealtimeInputConfig with all VAD settings."""
    config = types.RealtimeInputConfig(
        automatic_activity_detection=types.AutomaticActivityDetection(
            disabled=False,
            start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_HIGH,
            end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_LOW,
            silence_duration_ms=1000,
            prefix_padding_ms=300,
        ),
        activity_handling=types.ActivityHandling.START_OF_ACTIVITY_INTERRUPTS,
    )

    assert config.automatic_activity_detection is not None
    assert config.automatic_activity_detection.disabled is False
    assert config.automatic_activity_detection.silence_duration_ms == 1000
    assert config.automatic_activity_detection.prefix_padding_ms == 300
    assert config.activity_handling == types.ActivityHandling.START_OF_ACTIVITY_INTERRUPTS


def test_realtime_input_config_no_interruption():
    """Test creating RealtimeInputConfig without barge-in."""
    config = types.RealtimeInputConfig(
        automatic_activity_detection=types.AutomaticActivityDetection(
            disabled=False,
        ),
        activity_handling=types.ActivityHandling.NO_INTERRUPTION,
    )

    assert config.activity_handling == types.ActivityHandling.NO_INTERRUPTION


def test_live_connect_config_with_vad():
    """Test LiveConnectConfig can include VAD settings."""
    realtime_config = types.RealtimeInputConfig(
        automatic_activity_detection=types.AutomaticActivityDetection(
            disabled=False,
            start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_LOW,
            end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_HIGH,
            silence_duration_ms=500,
            prefix_padding_ms=200,
        ),
        activity_handling=types.ActivityHandling.START_OF_ACTIVITY_INTERRUPTS,
    )

    live_config = types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        realtime_input_config=realtime_config,
    )

    assert live_config.realtime_input_config is not None
    assert live_config.realtime_input_config.automatic_activity_detection is not None
    assert live_config.realtime_input_config.activity_handling == types.ActivityHandling.START_OF_ACTIVITY_INTERRUPTS


def test_vad_enum_values():
    """Test VAD enum string values are correct."""
    assert types.StartSensitivity.START_SENSITIVITY_HIGH.value == "START_SENSITIVITY_HIGH"
    assert types.StartSensitivity.START_SENSITIVITY_LOW.value == "START_SENSITIVITY_LOW"
    assert types.EndSensitivity.END_SENSITIVITY_HIGH.value == "END_SENSITIVITY_HIGH"
    assert types.EndSensitivity.END_SENSITIVITY_LOW.value == "END_SENSITIVITY_LOW"
    assert types.ActivityHandling.START_OF_ACTIVITY_INTERRUPTS.value == "START_OF_ACTIVITY_INTERRUPTS"
    assert types.ActivityHandling.NO_INTERRUPTION.value == "NO_INTERRUPTION"
