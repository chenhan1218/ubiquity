#include <stdlib.h>

#include <gtk/gtk.h>
#include <librsvg/rsvg.h>
#include <librsvg/rsvg-cairo.h>

static int        return_value = 0;
static gchar     *filename = NULL;
static GtkWidget *window = NULL;
static GtkWidget *image = NULL;
static GtkWidget *button1 = NULL;
static GtkWidget *button2 = NULL;
static GtkWidget *fixed = NULL;
static gdouble    button1_height = 0.5;
static gdouble    button2_height = 0.5;

static GOptionEntry entries[] = {
  {
    "filename", 'f', 0,
    G_OPTION_ARG_FILENAME, &filename,
    "Filename for SVG image", NULL
  },
  {
    "button1-y", '1', 0,
    G_OPTION_ARG_DOUBLE, &button1_height,
    "Button 1 height ratio", NULL
  },
  {
    "button2-y", '2', 0,
    G_OPTION_ARG_DOUBLE, &button2_height,
    "Button 2 height ratio", NULL
  },
  { NULL }
};

static gboolean
recompute_button_positions (gpointer data)
{
  int x, y;

  if (button1 != NULL)
    {
      x = window->allocation.width / 4 - button1->requisition.width / 2;
      y = window->allocation.height * button1_height;

      if (button1->allocation.x != x || button1->allocation.y != y)
        {
          gtk_fixed_move (GTK_FIXED (fixed),
                          button1,
                          window->allocation.width / 4 - button1->requisition.width / 2,
                          window->allocation.height * button1_height);
        }
    }

  if (button2 != NULL)
    {
      x = window->allocation.width * 0.75 - button2->requisition.width / 2;
      y = window->allocation.height * button2_height;

      if (button2->allocation.x != x || button2->allocation.y != y)
        {
          gtk_fixed_move (GTK_FIXED (fixed),
                          button2,
                          window->allocation.width * 0.75 - button2->requisition.width / 2,
                          window->allocation.height * button2_height);
        }
    }

  return FALSE;
}

static gboolean
button_mapped (GtkWidget *button,
               GtkWidget *fixed)
{
  g_timeout_add (100, recompute_button_positions, NULL);
}

static void
button1_clicked (GtkWidget      *button,
                 gpointer        user_data)
{
  return_value = 1;
  gtk_main_quit ();
}

static void
button2_clicked (GtkWidget  *button,
                 gpointer    user_data)
{
  return_value = 2;
  gtk_main_quit ();
}

static void
fixed_size_allocate (GtkWidget     *widget,
                     GtkAllocation *allocation,
                     gpointer       user_data)
{
  g_timeout_add (100, recompute_button_positions, NULL);
}

static void
window_size_allocate (GtkWidget     *widget,
                      GtkAllocation *allocation,
                      GtkWidget     *fixed)
{
  GdkPixbuf *pixbuf = rsvg_pixbuf_from_file_at_size ("test.svg",
                                                     allocation->width,
                                                     allocation->height,
                                                     NULL);

  if (image == NULL)
    {
      image = gtk_image_new_from_pixbuf (pixbuf);
      gtk_widget_show (image);
      gtk_fixed_put (GTK_FIXED (fixed),
                     image,
                     0, 0);

      button1 = gtk_button_new_with_label ("Try Ubuntu");
      g_signal_connect (button1, "clicked", G_CALLBACK (button1_clicked), NULL);
      g_signal_connect (button1, "map", G_CALLBACK (button_mapped), fixed);
      gtk_fixed_put (GTK_FIXED (fixed),
                     button1, 0, 0);
      gtk_widget_show (button1);

      button2 = gtk_button_new_with_label ("Install Ubuntu");
      g_signal_connect (button2, "clicked", G_CALLBACK (button2_clicked), NULL);
      g_signal_connect (button2, "map", G_CALLBACK (button_mapped), fixed);
      gtk_fixed_put (GTK_FIXED (fixed),
                     button2, 0, 0);
      gtk_widget_show (button2);
    }
  else
    {
      if (image->allocation.width != allocation->width &&
          image->allocation.height != allocation->height)
        {
          gtk_image_set_from_pixbuf (GTK_IMAGE (image), pixbuf);
        }
    }
}

int
main (int argc, char **argv)
{
  GOptionContext *context;

  gtk_init (&argc, &argv);
  rsvg_init ();

  context = g_option_context_new ("greeter");
  g_option_context_add_main_entries (context, entries, "greeter");
  g_option_context_add_group (context, gtk_get_option_group (TRUE));
  if (!g_option_context_parse (context, &argc, &argv, NULL))
    {
      exit (0);
    }

  window = gtk_window_new (GTK_WINDOW_TOPLEVEL);
  gtk_window_set_title (GTK_WINDOW (window), "Welcome to Ubuntu!");

  fixed = gtk_fixed_new ();
  gtk_container_add (GTK_CONTAINER (window), fixed);

  g_signal_connect (window, "size-allocate", G_CALLBACK (window_size_allocate), fixed);
  g_signal_connect (fixed, "size-allocate", G_CALLBACK (fixed_size_allocate), NULL);
  g_signal_connect (window, "delete-event", G_CALLBACK (gtk_main_quit), NULL);

  //gtk_window_fullscreen (GTK_WINDOW (window));
  gtk_widget_set_size_request (window, 1280, 1024);

  gtk_widget_show_all (window);

  gtk_main ();
  rsvg_term ();

  return return_value;
}
