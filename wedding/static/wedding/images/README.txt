Brian & Aisha Wedding — image asset inventory
==============================================

Last scanned: 2026-05-01

NOTE: All actual image files currently live in the project's media/ directory.
The wedding/static/wedding/images/<subfolder>/ directories below contain only
.gitkeep placeholders — no images have been copied into static yet.

------------------------------------------------------------
Inventory of image files found in the project
(organized by directory; sizes in bytes)
------------------------------------------------------------

media/ (root)
  bg-2.jpg                                                            83,871
  bouquet-img.png                                                     68,569
  bridal-scaled.jpg                                                  327,540
  closed-no-bg.png                                                   601,022
  cocktail-attire-for-men-a-dress-code-guide-382763.webp              31,298
  cocktail-attire-wedding-guest_9fb2de50-81d8-4a36-b821-
    67b07cc42215.webp                                                409,480
  Couple-Photo-2.png                                               1,018,435
  Couple-Photo.jpg                                                   842,804
  couple.jpg                                                         139,356
  fav.png                                                              7,176
  flower-4.png                                                       109,462
  flower-icon-01.png                                                   1,094
  flower-icon-02.png                                                  10,171
  h1-background-img-5-1.jpg                                           86,738
  icon-arrow-down.svg                                                    268
  img-1.png                                                          134,381
  img-2.png                                                          130,855
  Map-from-Pastiche.jpeg                                             295,350
  open-no-bg.png                                                     515,340
  pexels-photo-14716281-14716281-scaled.jpg                          755,657
  pexels-photo-16933510-16933510-scaled.jpg                          350,895
  pexels-photo-288008-288008-scaled.jpg                              315,705
  pexels-photo-3171837-3171837-scaled.jpg                            815,492
  pexels-photo-3309878-3309878-scaled.jpg                            284,470
  pexels-photo-34486584-34486584-scaled.jpg                          340,130
  rose-icon-01.png                                                     1,211
  Untitled-design-scaled.png                                       5,096,410
  wedding-1-scaled.jpg                                               937,707
  wedding-2-scaled.jpg                                               871,090
  wedding-4-scaled.jpg                                               799,770
  wedding-5-scaled.jpg                                               555,140
  wedding-6-scaled.jpg                                               555,958
  wedding3-scaled.jpg                                                856,263

media/accommodations/        (empty — only .gitkeep)
media/couple/                (empty — only .gitkeep)
media/events/                (empty — only .gitkeep)
media/faq/                   (empty — only .gitkeep)
media/story/                 (empty — only .gitkeep)

wedding/static/wedding/images/accommodations/   (empty — only .gitkeep)
wedding/static/wedding/images/couple/           (empty — only .gitkeep)
wedding/static/wedding/images/events/           (empty — only .gitkeep)
wedding/static/wedding/images/faq/              (empty — only .gitkeep)
wedding/static/wedding/images/home/             (empty — only .gitkeep)
wedding/static/wedding/images/story/            (empty — only .gitkeep)

------------------------------------------------------------
Where templates expect each image
(Django {% static 'wedding/images/<subfolder>/<filename>' %})
------------------------------------------------------------

couple/
  wedding-1-scaled.jpg     (homepage hero background, also referenced by story/)
  wedding-2.jpg            (gallery)
  wedding3.jpg             (gallery)
  wedding-4.jpg            (gallery)
  wedding-5.jpg            (gallery)
  wedding-6.jpg            (gallery)
  Couple-Photo-2.png       (gallery)

events/
  bridal-shower.jpg        (timeline item 1)
  bach-party-1.jpg         (timeline item 2 — left photo)
  bach-party-2.jpg         (timeline item 2 — right photo)
  wedding-venue.jpg        (timeline item 3)
  flower-icon-02.png       (page background, set inline on .page-bg-wrapper)

story/
  wedding-1-scaled.jpg     (story-page lead image)

faq/
  Map-from-Pastiche.jpeg    (parking map inside the Travel & Parking accordion)
  h1-background-img-5-1.jpg (page background, set inline on .page-bg-wrapper)

accommodations/
  flower-4.png             (page background, set inline on .page-bg-wrapper)

home/
  wedding-1-scaled.jpg     (homepage hero background — separate copy is fine)
  open-envelope.png        ("Close invitation" button at the bottom of the homepage)