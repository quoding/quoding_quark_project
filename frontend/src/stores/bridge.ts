/* QUARK — 디바이스 브리지 (단일 교체 지점).
 *
 * homeStore의 setter는 로컬 상태를 바꾼 뒤 이 cmd()를 호출한다.
 * 지금은 콘솔 로그만 남기지만, 추후 이 함수 본문만 MQTT publish
 * (hooks/useMqtt.ts의 클라이언트) 또는 Home Assistant REST 호출로
 * 교체하면 전체 UI가 실디바이스와 연결된다. 호출부는 손대지 않는다.
 */
export function cmd(deviceId: string, metric: string, value: unknown): void {
  // TODO(bridge): replace with MQTT publish — e.g.
  //   getMqttClient()?.publish(`quark/${deviceId}/${metric}/set`, String(value));
  if (import.meta.env.DEV) {
    // eslint-disable-next-line no-console
    console.debug('[bridge] cmd', deviceId, metric, value);
  }
}
