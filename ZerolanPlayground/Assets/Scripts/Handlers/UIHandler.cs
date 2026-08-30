using Controller.UI;
using Data;
using Framework;
using UnityEngine;

namespace Handlers
{
    [Handler]
    public class UIHandler : MonoBehaviour
    {
        [Inject] private MenuController MenuController { get; set; }

        [OnProtocolReceived(Action = Route.ShowMenu)]
        private void OnShowMenu(ShowTopMenu showMenu)
        {
            if (showMenu.DestroyLast)
            {
                MenuController.DestroyLast();
            }

            MenuController.GenerateButtons(showMenu.Items).Forget();
        }
    }
}