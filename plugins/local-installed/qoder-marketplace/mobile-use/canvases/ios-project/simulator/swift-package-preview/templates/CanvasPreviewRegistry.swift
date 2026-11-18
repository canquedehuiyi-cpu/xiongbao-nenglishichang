import Foundation
import SnapshotPreviewsCore
import SwiftUI

struct CanvasPreviewEntry: Identifiable {
  let id: String
  let group: String
  let name: String
  let makeView: @MainActor () -> AnyView
}

@MainActor
func discoverCanvasPreviews() -> [CanvasPreviewEntry] {
  let discovered = FindPreviews.findPreviews(
    included: nil,
    excluded: nil,
    includedModules: canvasPreviewModules,
    excludedModules: nil
  )

  var seenTypes = Set<String>()
  let newestRegistrations = discovered.reversed().filter { previewType in
    seenTypes.insert(previewType.typeName).inserted
  }.reversed()

  return newestRegistrations.flatMap { previewType in
    previewType.previews.enumerated().compactMap { index, preview in
      let displayName = preview.displayName ?? "Preview"
      guard canvasPreviewFilters?.contains(where: { filter in
        [previewType.typeName, previewType.displayName, displayName].contains {
          $0.range(of: filter, options: [.regularExpression, .caseInsensitive]) != nil
        }
      }) ?? true else {
        return nil
      }
      return CanvasPreviewEntry(
        id: "\(previewType.typeName):\(index)",
        group: previewType.displayName,
        name: displayName,
        makeView: { AnyView(preview.view()) }
      )
    }
  }
}
