import Darwin
import Foundation
import Observation
import SwiftUI

private enum CanvasPreviewIPC {
  static let notification = "dev.qoder.canvas.swiftui-preview.reload"
  static let directory = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
    .appendingPathComponent("qoder-swiftui-preview", isDirectory: true)
  static let manifest = directory.appendingPathComponent("reload.json")
  static let status = directory.appendingPathComponent("status.json")
}

private struct CanvasReloadManifest: Decodable {
  let token: String
  let dylibPath: String
}

private struct CanvasPreviewStatus: Encodable {
  let pid: Int
  let phase: String
  let token: String?
  let error: String?
}

private actor CanvasStatusWriter {
  func write(phase: String, token: String?, error: String?) {
    do {
      try FileManager.default.createDirectory(
        at: CanvasPreviewIPC.directory,
        withIntermediateDirectories: true
      )
      let payload = CanvasPreviewStatus(pid: Int(getpid()), phase: phase, token: token, error: error)
      try JSONEncoder().encode(payload).write(to: CanvasPreviewIPC.status, options: .atomic)
    } catch {
      print("Canvas preview status write failed: \(error.localizedDescription)")
    }
  }
}

private typealias CountFunction = @convention(c) () -> Int
private typealias StringFunction = @convention(c) (Int) -> UnsafeMutablePointer<CChar>?
private typealias FreeFunction = @convention(c) (UnsafeMutablePointer<CChar>?) -> Void
private typealias ViewFunction = @convention(c) (Int) -> UnsafeMutableRawPointer?

@MainActor
@Observable
private final class CanvasPreviewModel {
  private(set) var entries = discoverCanvasPreviews()
  var selectedIndex = 0

  @ObservationIgnored private var handles = [UnsafeMutableRawPointer]()
  @ObservationIgnored private var currentToken: String?
  @ObservationIgnored private let statusWriter = CanvasStatusWriter()
  @ObservationIgnored private var pendingStatus: Task<Void, Never>?

  init() {
    installReloadObserver()
    publish(phase: "running", token: nil, error: nil)
  }

  deinit {
    CFNotificationCenterRemoveObserver(
      CFNotificationCenterGetDarwinNotifyCenter(),
      UnsafeRawPointer(Unmanaged.passUnretained(self).toOpaque()),
      nil,
      nil
    )
  }

  func reloadFromManifest() {
    let manifest: CanvasReloadManifest
    do {
      manifest = try JSONDecoder().decode(
        CanvasReloadManifest.self,
        from: Data(contentsOf: CanvasPreviewIPC.manifest)
      )
    } catch {
      publish(phase: "error", token: currentToken, error: error.localizedDescription)
      return
    }
    guard manifest.token != currentToken else { return }

    guard let handle = dlopen(manifest.dylibPath, RTLD_NOW | RTLD_LOCAL) else {
      let message = dlerror().map { String(cString: $0) } ?? "unknown dlopen error"
      publish(phase: "error", token: manifest.token, error: message)
      return
    }
    handles.append(handle)

    guard let replacement = entries(from: handle, generation: manifest.token), !replacement.isEmpty else {
      publish(phase: "error", token: manifest.token, error: "No previews exported by reload dylib")
      return
    }
    currentToken = manifest.token
    entries = replacement
    selectedIndex = min(selectedIndex, max(0, replacement.count - 1))
    publish(phase: "reloaded", token: manifest.token, error: nil)
  }

  private func installReloadObserver() {
    let callback: CFNotificationCallback = { _, observer, _, _, _ in
      guard let observer else { return }
      let model = Unmanaged<CanvasPreviewModel>.fromOpaque(observer).takeUnretainedValue()
      Task { @MainActor in model.reloadFromManifest() }
    }
    CFNotificationCenterAddObserver(
      CFNotificationCenterGetDarwinNotifyCenter(),
      UnsafeRawPointer(Unmanaged.passUnretained(self).toOpaque()),
      callback,
      CanvasPreviewIPC.notification as CFString,
      nil,
      .deliverImmediately
    )
  }

  private func entries(from handle: UnsafeMutableRawPointer, generation: String) -> [CanvasPreviewEntry]? {
    guard
      let countSymbol = dlsym(handle, "qoder_canvas_preview_count"),
      let idSymbol = dlsym(handle, "qoder_canvas_preview_id"),
      let groupSymbol = dlsym(handle, "qoder_canvas_preview_group"),
      let nameSymbol = dlsym(handle, "qoder_canvas_preview_name"),
      let freeSymbol = dlsym(handle, "qoder_canvas_preview_free"),
      let viewSymbol = dlsym(handle, "qoder_canvas_preview_view")
    else { return nil }

    let count = unsafeBitCast(countSymbol, to: CountFunction.self)
    let readID = unsafeBitCast(idSymbol, to: StringFunction.self)
    let readGroup = unsafeBitCast(groupSymbol, to: StringFunction.self)
    let readName = unsafeBitCast(nameSymbol, to: StringFunction.self)
    let release = unsafeBitCast(freeSymbol, to: FreeFunction.self)
    let makeView = unsafeBitCast(viewSymbol, to: ViewFunction.self)

    func string(_ pointer: UnsafeMutablePointer<CChar>?) -> String? {
      guard let pointer else { return nil }
      defer { release(pointer) }
      return String(cString: pointer)
    }

    return (0..<count()).compactMap { index in
      guard
        let id = string(readID(index)),
        let group = string(readGroup(index)),
        let name = string(readName(index))
      else { return nil }
      return CanvasPreviewEntry(
        id: "\(generation):\(id)",
        group: group,
        name: name,
        makeView: {
          guard let raw = makeView(index) else { return AnyView(EmptyView()) }
          let pointer = raw.assumingMemoryBound(to: AnyView.self)
          let view = pointer.move()
          pointer.deallocate()
          return view
        }
      )
    }
  }

  private func publish(phase: String, token: String?, error: String?) {
    pendingStatus = Task { [statusWriter, previous = pendingStatus] in
      await previous?.value
      await statusWriter.write(phase: phase, token: token, error: error)
    }
  }
}

@main
@MainActor
struct QoderCanvasPreviewHostApp: App {
  var body: some Scene {
    WindowGroup { CanvasPreviewRoot() }
  }
}

@MainActor
private struct CanvasPreviewRoot: View {
  @State private var model = CanvasPreviewModel()

  var body: some View {
    if model.entries.isEmpty {
      ContentUnavailableView(
        "No SwiftUI previews",
        systemImage: "rectangle.on.rectangle.slash",
        description: Text("Add a #Preview to the selected Swift package target.")
      )
    } else {
      TabView(selection: $model.selectedIndex) {
        ForEach(Array(model.entries.enumerated()), id: \.element.id) { index, entry in
          entry.makeView().tag(index)
        }
      }
      .tabViewStyle(.page(indexDisplayMode: .never))
      .overlay(alignment: .topTrailing) {
        Menu {
          ForEach(Array(model.entries.enumerated()), id: \.element.id) { index, entry in
            Button("\(entry.group) — \(entry.name)") { model.selectedIndex = index }
          }
        } label: {
          Image(systemName: "ellipsis.circle.fill")
            .font(.title2)
            .symbolRenderingMode(.hierarchical)
            .padding(16)
        }
        .accessibilityLabel("Choose SwiftUI preview")
      }
    }
  }
}
