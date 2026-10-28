/**
 * Calls and lives through LiveKit (ADR-013). Only the call and live screens import this
 * file (they are downloaded on demand): the LiveKit library never weighs on other pages.
 *
 * Video adapts by itself to the network (adaptive stream, simulcast); on a weak network
 * the screens offer « audio only », which stops receiving (and sending) pictures.
 */
import {
  ConnectionQuality,
  DisconnectReason,
  Room,
  RoomEvent,
  Track,
  VideoPresets,
  type LocalVideoTrack,
  type Participant,
  type RemoteTrack,
  type RemoteTrackPublication,
  type VideoTrack,
} from "livekit-client";

export type RtcEvent = { type: string; [key: string]: unknown };

export type RtcCallbacks = {
  /** Somebody came, left, started or stopped a camera: read the room again. */
  onChange: () => void;
  /** An event of the platform (« reload the questions », « somebody bought »). */
  onData?: (event: RtcEvent) => void;
  /** The connection of this phone has been poor for a while (or is good again). */
  onWeak?: (weak: boolean) => void;
  /** Disconnected for good (hung up elsewhere, room closed, network lost). */
  onEnded?: (reason: "closed" | "network" | "left") => void;
  /** The browser refused to play the sound without a touch: show a button. */
  onAudioBlocked?: (blocked: boolean) => void;
};

/** A phone that saves data or a slow network: start without pictures. */
export function weakNetwork(dataSaver: boolean): boolean {
  if (dataSaver) return true;
  const connection = (
    navigator as Navigator & { connection?: { saveData?: boolean; effectiveType?: string } }
  ).connection;
  return Boolean(connection?.saveData || /(^|-)2g|3g/.test(connection?.effectiveType ?? ""));
}

const WEAK_AFTER_MS = 10_000;

export class RtcSession {
  readonly room: Room;
  private audioOnly = false;
  private weakTimer: number | null = null;
  private leaving = false;
  private sounds = new Set<HTMLMediaElement>();

  constructor(private callbacks: RtcCallbacks) {
    this.room = new Room({
      adaptiveStream: true,
      dynacast: true,
      videoCaptureDefaults: { resolution: VideoPresets.h540.resolution, facingMode: "user" },
      publishDefaults: { simulcast: true, videoSimulcastLayers: [VideoPresets.h180] },
    });
    const change = () => callbacks.onChange();
    this.room
      .on(RoomEvent.ParticipantConnected, change)
      .on(RoomEvent.ParticipantDisconnected, change)
      .on(RoomEvent.TrackPublished, change)
      .on(RoomEvent.TrackUnpublished, change)
      .on(RoomEvent.TrackMuted, change)
      .on(RoomEvent.TrackUnmuted, change)
      .on(RoomEvent.LocalTrackPublished, change)
      .on(RoomEvent.LocalTrackUnpublished, change)
      .on(RoomEvent.ParticipantPermissionsChanged, change)
      .on(RoomEvent.Reconnecting, change)
      .on(RoomEvent.Reconnected, change)
      .on(RoomEvent.TrackSubscribed, (track, publication) => this.subscribed(track, publication))
      .on(RoomEvent.TrackUnsubscribed, (track) => {
        track.detach().forEach((element) => {
          this.sounds.delete(element);
          element.remove();
        });
        change();
      })
      .on(RoomEvent.TrackPublished, (publication) => {
        if (this.audioOnly && publication.kind === Track.Kind.Video) {
          publication.setSubscribed(false);
        }
      })
      .on(RoomEvent.AudioPlaybackStatusChanged, () =>
        callbacks.onAudioBlocked?.(!this.room.canPlaybackAudio),
      )
      .on(RoomEvent.ConnectionQualityChanged, (quality, participant) =>
        this.quality(quality, participant),
      )
      .on(RoomEvent.DataReceived, (payload, _participant, _kind, topic) => {
        if (topic !== "sg") return;
        try {
          callbacks.onData?.(JSON.parse(new TextDecoder().decode(payload)) as RtcEvent);
        } catch {
          // Not an event of the platform.
        }
      })
      .on(RoomEvent.Disconnected, (reason) => {
        this.clearWeak();
        if (this.leaving) return;
        const closed =
          reason === DisconnectReason.ROOM_DELETED ||
          reason === DisconnectReason.PARTICIPANT_REMOVED ||
          reason === DisconnectReason.DUPLICATE_IDENTITY;
        callbacks.onEnded?.(closed ? "closed" : "network");
      });
  }

  async connect(url: string, token: string, { audioOnly = false } = {}): Promise<void> {
    this.audioOnly = audioOnly;
    await this.room.connect(url, token, { autoSubscribe: true });
    this.applyAudioOnly();
    this.callbacks.onAudioBlocked?.(!this.room.canPlaybackAudio);
  }

  /** The sound is allowed after a touch (some browsers block it before). */
  async allowAudio(): Promise<void> {
    await this.room.startAudio();
  }

  private subscribed(track: RemoteTrack, publication: RemoteTrackPublication) {
    if (track.kind === Track.Kind.Audio) {
      const element = track.attach();
      element.hidden = true;
      this.sounds.add(element);
      document.body.appendChild(element);
    } else if (this.audioOnly) {
      publication.setSubscribed(false);
    }
    this.callbacks.onChange();
  }

  private quality(quality: ConnectionQuality, participant: Participant) {
    if (participant.identity !== this.room.localParticipant.identity) return;
    if (quality === ConnectionQuality.Poor || quality === ConnectionQuality.Lost) {
      if (this.weakTimer === null) {
        this.weakTimer = window.setTimeout(() => this.callbacks.onWeak?.(true), WEAK_AFTER_MS);
      }
    } else {
      this.clearWeak();
      this.callbacks.onWeak?.(false);
    }
  }

  private clearWeak() {
    if (this.weakTimer !== null) window.clearTimeout(this.weakTimer);
    this.weakTimer = null;
  }

  async setMicrophone(on: boolean): Promise<void> {
    await this.room.localParticipant.setMicrophoneEnabled(on);
    this.callbacks.onChange();
  }

  async setCamera(on: boolean): Promise<void> {
    await this.room.localParticipant.setCameraEnabled(on);
    this.callbacks.onChange();
  }

  async flipCamera(): Promise<void> {
    const track = this.room.localParticipant.getTrackPublication(Track.Source.Camera)?.track as
      LocalVideoTrack | undefined;
    if (!track) return;
    const facing = track.mediaStreamTrack.getSettings().facingMode === "environment";
    await track.restartTrack({ facingMode: facing ? "user" : "environment" });
  }

  /** Audio only: no pictures received (and none sent by this phone). */
  async setAudioOnly(on: boolean): Promise<void> {
    this.audioOnly = on;
    this.applyAudioOnly();
    if (on && this.room.localParticipant.isCameraEnabled) await this.setCamera(false);
    this.callbacks.onChange();
  }

  get isAudioOnly(): boolean {
    return this.audioOnly;
  }

  private applyAudioOnly() {
    for (const participant of this.room.remoteParticipants.values()) {
      for (const publication of participant.videoTrackPublications.values()) {
        publication.setSubscribed(!this.audioOnly);
      }
    }
  }

  get micOn(): boolean {
    return this.room.localParticipant.isMicrophoneEnabled;
  }

  get cameraOn(): boolean {
    return this.room.localParticipant.isCameraEnabled;
  }

  /** May she send her voice (a viewer once the host gives her the floor)? */
  get canSpeak(): boolean {
    const permissions = this.room.localParticipant.permissions;
    return Boolean(permissions?.canPublish);
  }

  localVideo(): VideoTrack | undefined {
    return this.room.localParticipant.getTrackPublication(Track.Source.Camera)?.videoTrack;
  }

  /** The camera of one person (the host of a live), or of the first other person. */
  remoteVideo(identity?: string): VideoTrack | undefined {
    for (const participant of this.room.remoteParticipants.values()) {
      if (identity && participant.identity !== identity) continue;
      const publication = participant.getTrackPublication(Track.Source.Camera);
      if (publication?.isSubscribed && publication.videoTrack && !publication.isMuted) {
        return publication.videoTrack;
      }
    }
    return undefined;
  }

  get othersCount(): number {
    return this.room.remoteParticipants.size;
  }

  get reconnecting(): boolean {
    return this.room.state === "reconnecting";
  }

  async leave(): Promise<void> {
    this.leaving = true;
    this.clearWeak();
    await this.room.disconnect();
    this.sounds.forEach((element) => element.remove());
    this.sounds.clear();
  }
}
