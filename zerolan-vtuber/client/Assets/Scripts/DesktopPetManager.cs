using System;
using System.Collections;
using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.EventSystems;

public class DesktopPetManager : MonoBehaviour
{
    #region Windows API

    [DllImport("user32.dll")]
    private static extern IntPtr GetActiveWindow();

    [DllImport("user32.dll")]
    private static extern IntPtr GetForegroundWindow();

    [DllImport("user32.dll")]
    private static extern int SetWindowLong(IntPtr hWnd, int nIndex, uint dwNewLong);

    [DllImport("user32.dll")]
    private static extern uint GetWindowLong(IntPtr hWnd, int nIndex);

    [DllImport("user32.dll")]
    private static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int x, int y, int cx, int cy, uint uFlags);

    [DllImport("dwmapi.dll")]
    private static extern int DwmExtendFrameIntoClientArea(IntPtr hwnd, ref MARGINS margins);

    [DllImport("user32.dll")]
    private static extern bool GetCursorPos(out POINT lpPoint);

    [DllImport("user32.dll")]
    private static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    private static extern bool SetLayeredWindowAttributes(IntPtr hwnd, uint crKey, byte bAlpha, uint dwFlags);

    [StructLayout(LayoutKind.Sequential)]
    private struct MARGINS { public int left, right, top, bottom; }

    [StructLayout(LayoutKind.Sequential)]
    public struct POINT { public int x, y; }

    [DllImport("user32.dll")]
    private static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);

    [StructLayout(LayoutKind.Sequential)]
    private struct RECT { public int left, top, right, bottom; }

    private const int GWL_EXSTYLE = -20;
    private const uint WS_EX_LAYERED = 0x00080000;
    private static readonly IntPtr HWND_TOPMOST = new IntPtr(-1);
    private const uint SWP_NOACTIVATE = 0x0010;
    private const uint SWP_NOMOVE = 0x0002;
    private const uint SWP_NOSIZE = 0x0001;
    private const uint SWP_SHOWWINDOW = 0x0040;
    private const uint LWA_COLORKEY = 0x00000001;
    // 纯黑会被 UI 大量用作背景/文字色（设置面板 0,0,0,0.78 等），colorkey 抠黑会把它们
    // 连带抠成透明 + 点击穿透（失焦→runInBackground:0 冻结主循环，表现为"点 UI 就闪退"）。
    // 改抠品红 (2,0,2)：UI 不会用到，相机清屏色同步为同色即可抠掉窗口底色。
    private const uint TRANSPARENT_COLOR = 0x000202; // COLORREF = 0x00BBGGRR → R=2,G=0,B=2

    #endregion

    [Header("Settings")]
    [SerializeField] private bool enableDrag = true;

    private IntPtr _hwnd;
    private Camera _mainCamera;
    private bool _isDragging;
    private POINT _dragStartScreen;
    private RECT _windowStartRect;
    private bool _isTransparentMode;

    private void Awake()
    {
        #if !UNITY_EDITOR && UNITY_STANDALONE_WIN
        _mainCamera = Camera.main;
        if (_mainCamera == null)
        {
            Debug.LogError("[DesktopPet] No main camera found.");
            enabled = false;
        }
        #endif
    }

    /// <summary>
    /// Switch to transparent desktop pet mode. Call this after the model is loaded.
    /// </summary>
    public void EnterTransparentMode()
    {
        #if !UNITY_EDITOR && UNITY_STANDALONE_WIN
        if (_isTransparentMode) return;
        InitCamera();
        StartCoroutine(InitTransparentWindowDeferred());
        #endif
    }

    private IEnumerator InitTransparentWindowDeferred()
    {
        yield return new WaitForEndOfFrame();
        yield return null;
        InitTransparentWindow();
    }

    private void InitTransparentWindow()
    {
        _hwnd = GetForegroundWindow();
        if (_hwnd == IntPtr.Zero)
            _hwnd = GetActiveWindow();
        if (_hwnd == IntPtr.Zero)
        {
            Debug.LogError("[DesktopPet] Failed to get window handle.");
            return;
        }

        var margins = new MARGINS { left = -1, right = -1, top = -1, bottom = -1 };
        DwmExtendFrameIntoClientArea(_hwnd, ref margins);

        var style = GetWindowLong(_hwnd, GWL_EXSTYLE);
        SetWindowLong(_hwnd, GWL_EXSTYLE, style | WS_EX_LAYERED);
        SetLayeredWindowAttributes(_hwnd, TRANSPARENT_COLOR, 0, LWA_COLORKEY);

        SetWindowPos(_hwnd, HWND_TOPMOST, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_SHOWWINDOW);

        _isTransparentMode = true;
        Debug.Log("[DesktopPet] Transparent window initialized.");
    }

    private void InitCamera()
    {
        _mainCamera.clearFlags = CameraClearFlags.SolidColor;
        // 与 TRANSPARENT_COLOR(colorkey) 同色：窗口底色被整片抠掉，UI 正常色不受影响
        _mainCamera.backgroundColor = new Color(2f / 255f, 0f, 2f / 255f, 1f);
        _mainCamera.targetTexture = null;
    }

    private void Update()
    {
        #if !UNITY_EDITOR && UNITY_STANDALONE_WIN
        if (!_isTransparentMode) return;

        HandleDrag();
        HandleQuit();
        #endif
    }

    private void HandleDrag()
    {
        if (!enableDrag) return;

        if (Input.GetMouseButtonDown(0))
        {
            if (EventSystem.current != null && EventSystem.current.IsPointerOverGameObject()) return;

            _isDragging = true;
            GetCursorPos(out _dragStartScreen);
            GetWindowRect(_hwnd, out _windowStartRect);
            SetForegroundWindow(_hwnd);
        }

        if (_isDragging && Input.GetMouseButton(0))
        {
            GetCursorPos(out var currentPos);
            var dx = currentPos.x - _dragStartScreen.x;
            var dy = currentPos.y - _dragStartScreen.y;
            SetWindowPos(_hwnd, HWND_TOPMOST,
                _windowStartRect.left + dx,
                _windowStartRect.top + dy,
                _windowStartRect.right - _windowStartRect.left,
                _windowStartRect.bottom - _windowStartRect.top,
                SWP_SHOWWINDOW);
        }

        if (Input.GetMouseButtonUp(0))
        {
            _isDragging = false;
        }
    }

    private void HandleQuit()
    {
        if (Input.GetKeyDown(KeyCode.Escape))
        {
            // 输入框聚焦时 ESC 是"取消焦点"，不退应用（透明模式激活后此按键才会生效）
            var es = EventSystem.current;
            if (es != null && es.currentSelectedGameObject != null) return;
            Application.Quit();
        }
    }
}
