#ifndef _UBIQUITY_WEBCAM_H
#define _UBIQUITY_WEBCAM_H

#include <gtk/gtk.h>
#include <gdk/gdkx.h>
#include <gst/gst.h>
#include <gst/interfaces/xoverlay.h>


G_BEGIN_DECLS

#define UBIQUITY_TYPE_WEBCAM ubiquity_webcam_get_type()

#define UBIQUITY_WEBCAM(obj) \
  (G_TYPE_CHECK_INSTANCE_CAST ((obj), \
  UBIQUITY_TYPE_WEBCAM, UbiquityWebcam))

#define UBIQUITY_WEBCAM_CLASS(klass) \
  (G_TYPE_CHECK_CLASS_CAST ((klass), \
  UBIQUITY_TYPE_WEBCAM, UbiquityWebcamClass))

#define UBIQUITY_IS_WEBCAM(obj) \
  (G_TYPE_CHECK_INSTANCE_TYPE ((obj), \
  UBIQUITY_TYPE_WEBCAM))

#define UBIQUITY_IS_WEBCAM_CLASS(klass) \
  (G_TYPE_CHECK_CLASS_TYPE ((klass), \
  UBIQUITY_TYPE_WEBCAM))

#define UBIQUITY_GET_CLASS(obj) \
  (G_TYPE_INSTANCE_GET_CLASS ((obj), \
  UBIQUITY_TYPE_WEBCAM, UbiquityWebcamClass))

typedef struct _UbiquityWebcam UbiquityWebcam;
typedef struct _UbiquityWebcamClass UbiquityWebcamClass;
typedef struct _UbiquityWebcamPrivate UbiquityWebcamPrivate;

struct _UbiquityWebcam
{
  GtkVBox parent;

  UbiquityWebcamPrivate *priv;
};

struct _UbiquityWebcamClass
{
  GtkVBoxClass parent_class;
};

GType ubiquity_webcam_get_type (void) G_GNUC_CONST;

UbiquityWebcam *ubiquity_webcam_new (void);
void ubiquity_webcam_play (UbiquityWebcam *webcam);
void ubiquity_webcam_stop (UbiquityWebcam *webcam);
gboolean ubiquity_webcam_available (void);

G_END_DECLS

#endif /* _UBIQUITY_WEBCAM_H */

