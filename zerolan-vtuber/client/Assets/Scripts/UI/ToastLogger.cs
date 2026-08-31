using System.Collections.Generic;
using System.Threading;
using Controller;
using Cysharp.Threading.Tasks;
using UnityEngine;
using UnityEngine.Assertions;

namespace UI
{
    internal class Args
    {
        public string Text { get; set; }
        public ToastType Level { get; set; }
    }

    public class ToastLogger : MonoBehaviour
    {
        [SerializeField] private Canvas toastCanvas;
        [SerializeField] private ChatHistoryController chatHistoryController;
        private GameObject _toastPrefab;
        private static readonly Queue<Args> ShowToastTasksQueue = new();
        private static ToastLogger _instance;
        private CancellationTokenSource _loopCts;

        private void Awake()
        {
            if (_instance != null && _instance != this)
            {
                Destroy(gameObject);
                return;
            }
            _instance = this;
        }

        private void Start()
        {
            Assert.IsNotNull(toastCanvas);
            _toastPrefab = Resources.Load<GameObject>("Prefabs/Toast");
            Assert.IsNotNull(_toastPrefab);
            Assert.IsNotNull(chatHistoryController);
            _loopCts = new CancellationTokenSource();
            RunEventLoop(_loopCts.Token).Forget();
        }

        private void OnDestroy()
        {
            if (_instance == this)
            {
                _loopCts?.Cancel();
                _loopCts?.Dispose();
                _instance = null;
            }
        }

        private async UniTaskVoid RunEventLoop(CancellationToken cancellationToken)
        {
            while (!cancellationToken.IsCancellationRequested)
            {
                await UniTask.WaitUntil(() => ShowToastTasksQueue.Count > 0, cancellationToken: cancellationToken).SuppressCancellationThrow();
                if (cancellationToken.IsCancellationRequested) break;
                var args = ShowToastTasksQueue.Dequeue();
                Show(args.Text, args.Level).Forget();
            }
        }

        private async UniTask Show(string text, ToastType level)
        {
            var toastGo = Instantiate(_toastPrefab, toastCanvas.transform);
            var toastComp = toastGo.GetComponent<Toast>();
            chatHistoryController.AddSystemBubble(text);
            await toastComp.Show(text, level);
        }

        public static void Info(string text)
        {
            ShowToastTasksQueue.Enqueue(new Args { Text = text, Level = ToastType.Info });
        }

        public static void Warning(string text)
        {
            ShowToastTasksQueue.Enqueue(new Args { Text = text, Level = ToastType.Warning });
        }

        public static void Error(string text)
        {
            ShowToastTasksQueue.Enqueue(new Args { Text = text, Level = ToastType.Error });
        }

        public static void StopEventLoop()
        {
            _instance?._loopCts?.Cancel();
        }
    }
}