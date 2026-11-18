import Darwin
import Foundation
import SwiftUI

@MainActor private let reloadEntries = discoverCanvasPreviews()

private func copiedCString(_ value: String) -> UnsafeMutablePointer<CChar>? {
  strdup(value)
}

@_cdecl("qoder_canvas_preview_count")
public func qoderCanvasPreviewCount() -> Int {
  MainActor.assumeIsolated { reloadEntries.count }
}

@MainActor
@_cdecl("qoder_canvas_preview_id")
public func qoderCanvasPreviewID(_ index: Int) -> UnsafeMutablePointer<CChar>? {
  guard reloadEntries.indices.contains(index) else { return nil }
  return copiedCString(reloadEntries[index].id)
}

@MainActor
@_cdecl("qoder_canvas_preview_group")
public func qoderCanvasPreviewGroup(_ index: Int) -> UnsafeMutablePointer<CChar>? {
  guard reloadEntries.indices.contains(index) else { return nil }
  return copiedCString(reloadEntries[index].group)
}

@MainActor
@_cdecl("qoder_canvas_preview_name")
public func qoderCanvasPreviewName(_ index: Int) -> UnsafeMutablePointer<CChar>? {
  guard reloadEntries.indices.contains(index) else { return nil }
  return copiedCString(reloadEntries[index].name)
}

@_cdecl("qoder_canvas_preview_free")
public func qoderCanvasPreviewFree(_ pointer: UnsafeMutablePointer<CChar>?) {
  free(pointer)
}

@MainActor
@_cdecl("qoder_canvas_preview_view")
public func qoderCanvasPreviewView(_ index: Int) -> UnsafeMutableRawPointer? {
  guard reloadEntries.indices.contains(index) else { return nil }
  let storage = UnsafeMutablePointer<AnyView>.allocate(capacity: 1)
  storage.initialize(to: reloadEntries[index].makeView())
  return UnsafeMutableRawPointer(storage)
}
