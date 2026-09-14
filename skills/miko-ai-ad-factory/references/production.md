# Production contract

## Characters and voices

Text-described characters are the default for this factory. Define consistent identifiers, contrasting voices, physical appearance, clothing, eyelines and roles in the prompt. Do not create character reference images. With multiple dependent jobs, reuse descriptions and propose an accepted generated continuation excerpt where needed; text alone does not guarantee identical casting across independent generations.

Offer two optional audio samples for a two-person podcast. Ask which belongs to which speaker and confirm use rights/consent. Probe duration, isolate clean speech and keep combined audio within the active limit. State explicitly that @Audio1 is the first speaker's vocal reference and @Audio2 the second's; sample speech is not the ad script. Put exact new dialogue beside the correct speaker. Review voices and turn-taking after generation. If no samples supplied, use described original voices.

## Graphic preparation

For a paper collage like the supplied example: extract a representative frame for analysis; identify paper layers, torn edges, typography, shadows, angle and movement. Use Nano Banana Pro image editing with that authorized layout reference and the product's own assets to prepare the adapted graphic. Exclude original subtitles. Replace original names/logos/content, and use only supported claims. Prefer an explicitly designed editorial card over pretending an invented newspaper or doctor substantiates the product.

Proofread all important text. If the image model corrupts it, use deterministic typesetting before video. Store the accepted image as `graphic_01`; upload only that accepted asset for generation. Prompt the scene explicitly: when graphic_01 appears, relative motion of paper layers, subtle source-derived push/parallax, hold, cut to next beat. Generated video can still distort text; QA and replace with a deterministic animated graphic if needed.

No graphics are mandatory when the reference doesn't have them. Product stills, graphic stills, optional licensed motion excerpts and voice samples each have explicit roles. They are not interchangeable and should not redefine a talking character's appearance accidentally.

## Seedance prompt layout

1. Output duration, aspect ratio, realism and environment.
2. Speaker descriptions and voice mapping; product facts and reference asset map.
3. Timecoded scenes: camera/crop/movement, performance, exact dialogue, product action, B-roll/graphic reference and motion, transition.
4. Continuity and audio bridges across scenes.
5. Exclusions: no subtitles, captions, transcript text, lower thirds or dialogue overlays; no unintended text, extra speakers or invented brand/claims. Approved embedded graphic text/product labels remain permitted.

Use detailed prompts up to provider limits. Do not pretend the natural-language scene timestamps are hard execution guarantees. Request native synchronized audio for dialogue when appropriate.

For ads longer than one job, plan <=30s chunks at natural boundaries. Independent B-roll can run alongside other work; dependent dialogue/continuation must wait for accepted output. A video-reference continuation is not an authenticated native extend feature; don't invent `extension_task_id` behavior. Respect reference video duration and normalization limits. Budget charges both input and output seconds in video-reference mode.

## Final review

Compare full output to the approved storyboard and source-derived treatment. Check all scenes, timing, faces, hands, labels, graphic text, voice assignment, dialogue completeness, lip sync, continuity and end. Repair exact cuts/simple crops in editing; do not add a generic retention preset. Reject generated subtitles rather than declaring prompt exclusion successful by itself. No automatic captions later.

Keep a before/after edit log and originals. Optional metadata sanitization is a separate export operation preserving required provenance and disclosures, not a way to evade platform policies.
